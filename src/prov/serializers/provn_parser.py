"""Recursive-descent parser for PROV-N (https://www.w3.org/TR/prov-n/).

Every statement opens with a keyword, so the parser reads one token and
enters the matching rule; there is no backtracking. Records are built
through :meth:`ProvBundle.new_record` with the same arguments the PROV-JSON
deserializer passes, so attribute typing, literal parsing and namespace
registration match every other format.

Profiles:

- ``strict``: the Recommendation grammar only.
- ``default``: also the de-facto extensions ``prov`` and ProvToolbox write,
  the bare ``mentionOf`` keyword and the shorthand keywords for typed
  agents, entities and derivations.
- ``lenient``: as ``default``; a statement that fails to parse is skipped
  with a :class:`ProvWarning` and parsing resumes at the next statement.
  Tokenisation errors are fatal in every profile.
"""

from __future__ import annotations

import warnings
from typing import Any

from prov.constants import (
    PROV,
    PROV_ACTIVITY,
    PROV_AGENT,
    PROV_ALTERNATE,
    PROV_ASSOCIATION,
    PROV_ATTRIBUTE_LITERALS,
    PROV_ATTRIBUTION,
    PROV_COMMUNICATION,
    PROV_DELEGATION,
    PROV_DERIVATION,
    PROV_END,
    PROV_ENTITY,
    PROV_GENERATION,
    PROV_INFLUENCE,
    PROV_INVALIDATION,
    PROV_MEMBERSHIP,
    PROV_MENTION,
    PROV_QUALIFIEDNAME,
    PROV_SPECIALIZATION,
    PROV_START,
    PROV_USAGE,
)
from prov.identifier import Namespace, QualifiedName
from prov.model import (
    PROV_REC_CLS,
    Literal,
    ProvBundle,
    ProvDocument,
    ProvException,
    ProvWarning,
    parse_xsd_datetime,
)
from prov.serializers.provn_lexer import ProvNSyntaxError, Token, TokenKind, tokenize

__all__ = ["PROFILES", "ProvNParser"]

PROFILES = ("strict", "default", "lenient")

# keyword -> (record type, allowed argument counts after the identifier)
_ELEMENTS: dict[str, tuple[QualifiedName, tuple[int, ...]]] = {
    "entity": (PROV_ENTITY, (0,)),
    "activity": (PROV_ACTIVITY, (0, 2)),
    "agent": (PROV_AGENT, (0,)),
}
# keyword -> (record type, allowed argument counts)
_RELATIONS: dict[str, tuple[QualifiedName, tuple[int, ...]]] = {
    "wasGeneratedBy": (PROV_GENERATION, (1, 3)),
    "used": (PROV_USAGE, (1, 3)),
    "wasInvalidatedBy": (PROV_INVALIDATION, (1, 3)),
    "wasStartedBy": (PROV_START, (1, 4)),
    "wasEndedBy": (PROV_END, (1, 4)),
    "wasInformedBy": (PROV_COMMUNICATION, (2,)),
    "wasAttributedTo": (PROV_ATTRIBUTION, (2,)),
    "wasAssociatedWith": (PROV_ASSOCIATION, (1, 3)),
    "actedOnBehalfOf": (PROV_DELEGATION, (2, 3)),
    "wasDerivedFrom": (PROV_DERIVATION, (2, 5)),
    "wasInfluencedBy": (PROV_INFLUENCE, (2,)),
    "alternateOf": (PROV_ALTERNATE, (2,)),
    "specializationOf": (PROV_SPECIALIZATION, (2,)),
    "hadMember": (PROV_MEMBERSHIP, (2,)),
}
_MENTION: tuple[QualifiedName, tuple[int, ...]] = (PROV_MENTION, (3,))
# default-profile shorthand keyword -> (base keyword, asserted prov:type)
_SHORTHAND: dict[str, tuple[str, QualifiedName]] = {
    "person": ("agent", PROV["Person"]),
    "organization": ("agent", PROV["Organization"]),
    "softwareAgent": ("agent", PROV["SoftwareAgent"]),
    "collection": ("entity", PROV["Collection"]),
    "emptyCollection": ("entity", PROV["EmptyCollection"]),
    "plan": ("entity", PROV["Plan"]),
    "wasRevisionOf": ("wasDerivedFrom", PROV["Revision"]),
    "wasQuotedFrom": ("wasDerivedFrom", PROV["Quotation"]),
    "hadPrimarySource": ("wasDerivedFrom", PROV["PrimarySource"]),
}
_STRUCTURAL = frozenset({"document", "endDocument", "bundle", "endBundle"})
_ARGUMENT_KINDS = (TokenKind.NAME, TokenKind.MARKER, TokenKind.DATETIME)


class ProvNParser:
    """Parse one PROV-N document.

    Args:
        text: The PROV-N source.
        profile: One of :data:`PROFILES`.

    Raises:
        ValueError: If ``profile`` is not one of :data:`PROFILES`.
    """

    def __init__(self, text: str, profile: str = "default"):
        if profile not in PROFILES:
            raise ValueError(f"profile must be one of {PROFILES}, got {profile!r}")
        self.profile = profile
        self._text = text
        self._tokens: list[Token] = []
        self._pos = 0

    # -- token helpers -----------------------------------------------------

    @property
    def _current(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        token = self._tokens[self._pos]
        if self._pos < len(self._tokens) - 1:
            self._pos += 1
        return token

    def _error(self, message: str, token: Token | None = None) -> ProvNSyntaxError:
        token = token or self._current
        return ProvNSyntaxError(message, token.line, token.column)

    def _found(self) -> str:
        token = self._current
        return token.kind.value if token.kind is TokenKind.EOF else repr(token.text)

    def _expect(self, kind: TokenKind, what: str | None = None) -> Token:
        if self._current.kind is not kind:
            expected = what if what is not None else repr(kind.value)
            raise self._error(f"expected {expected}, found {self._found()}")
        return self._advance()

    def _at_keyword(self, keyword: str) -> bool:
        return self._current.kind is TokenKind.NAME and self._current.value == (
            "",
            keyword,
        )

    def _expect_keyword(self, keyword: str) -> None:
        if not self._at_keyword(keyword):
            raise self._error(f"expected '{keyword}', found {self._found()}")
        self._advance()

    # -- structure -------------------------------------------------------------

    def parse(self) -> ProvDocument:
        """Parse the whole input and return the document."""
        self._tokens = list(tokenize(self._text))
        self._pos = 0
        document = ProvDocument()
        self._expect_keyword("document")
        self._declarations(document)
        while not self._at_keyword("endDocument"):
            if self._current.kind is TokenKind.EOF:
                raise self._error("expected 'endDocument', found end of input")
            if self._at_keyword("bundle"):
                self._bundle(document)
            else:
                self._statement(document)
        self._advance()
        if self._current.kind is not TokenKind.EOF:
            raise self._error("unexpected content after 'endDocument'")
        return document

    def _declarations(self, bundle: ProvBundle) -> None:
        while True:
            if self._at_keyword("prefix"):
                self._advance()
                name = self._expect(TokenKind.NAME, "a prefix")
                prefix, local = name.value
                if prefix:
                    raise self._error(f"expected a prefix, found {name.text!r}", name)
                iri = self._expect(TokenKind.IRI, "an IRI in angle brackets")
                bundle.add_namespace(Namespace(local, iri.value))
            elif self._at_keyword("default"):
                self._advance()
                iri = self._expect(TokenKind.IRI, "an IRI in angle brackets")
                bundle.set_default_namespace(iri.value)
            else:
                return

    def _bundle(self, document: ProvDocument) -> None:
        self._advance()  # 'bundle'
        identifier = self._identifier(document)
        bundle = document.bundle(identifier)
        self._declarations(bundle)
        while not self._at_keyword("endBundle"):
            if self._current.kind is TokenKind.EOF:
                raise self._error("expected 'endBundle', found end of input")
            if self._at_keyword("bundle"):
                raise self._error("a bundle cannot contain a bundle")
            self._statement(bundle)
        self._advance()

    def _statement(self, bundle: ProvBundle) -> None:
        start = self._current
        try:
            self._expression(bundle)
        except ProvNSyntaxError as exc:
            if self.profile != "lenient":
                raise
            warnings.warn(f"PROV-N statement skipped: {exc}", ProvWarning, stacklevel=3)
            self._resync()
        except ProvException as exc:
            raise ProvNSyntaxError(str(exc), start.line, start.column) from exc

    def _resync(self) -> None:
        """Skip to the next statement boundary at bracket depth zero."""
        depth = 0
        while self._current.kind is not TokenKind.EOF:
            token = self._current
            if token.kind in (TokenKind.LPAREN, TokenKind.LBRACKET):
                depth += 1
            elif token.kind in (TokenKind.RPAREN, TokenKind.RBRACKET):
                depth = max(0, depth - 1)
            elif depth == 0 and token.kind is TokenKind.NAME:
                prefix, local = token.value
                if not prefix and (
                    local in _STRUCTURAL
                    or local in _ELEMENTS
                    or local in _RELATIONS
                    or local in _SHORTHAND
                    or local == "mentionOf"
                ):
                    return
                if (prefix, local) == ("prov", "mentionOf"):
                    return
            self._advance()

    # -- expressions -------------------------------------------------------------

    def _classify(
        self, token: Token
    ) -> tuple[QualifiedName, tuple[int, ...], bool, QualifiedName | None]:
        """Return (record type, arities, is_element, asserted type) for a keyword token."""
        prefix, local = token.value
        extensions = self.profile != "strict"
        if (prefix, local) == ("prov", "mentionOf") or (
            extensions and (prefix, local) == ("", "mentionOf")
        ):
            return (*_MENTION, False, None)
        if prefix:
            raise self._error(
                f"extensibility expression '{token.text}(...)' is not supported", token
            )
        if local in _ELEMENTS:
            return (*_ELEMENTS[local], True, None)
        if local in _RELATIONS:
            return (*_RELATIONS[local], False, None)
        if extensions and local in _SHORTHAND:
            base, asserted = _SHORTHAND[local]
            if base in _ELEMENTS:
                return (*_ELEMENTS[base], True, asserted)
            return (*_RELATIONS[base], False, asserted)
        raise self._error(f"unknown statement keyword '{local}'", token)

    def _expression(self, bundle: ProvBundle) -> None:
        keyword = self._expect(TokenKind.NAME, "a statement keyword")
        rec_type, arities, is_element, asserted_type = self._classify(keyword)
        self._expect(TokenKind.LPAREN, "'('")
        identifier: QualifiedName | None = None
        args: list[Token] = []
        if is_element:
            identifier = self._identifier(bundle)
        else:
            first = self._argument()
            if self._current.kind is TokenKind.SEMICOLON:
                if first.kind is not TokenKind.NAME:
                    raise self._error("expected an identifier before ';'", first)
                identifier = self._resolve(first, bundle)
                self._advance()
                args.append(self._argument())
            else:
                args.append(first)
        other_attributes: list[tuple[QualifiedName, Any]] = []
        while True:
            separator_kind = self._current.kind
            if separator_kind is not TokenKind.COMMA:
                break
            self._advance()
            if self._current.kind is TokenKind.LBRACKET:
                other_attributes = self._attributes(bundle)
                break
            args.append(self._argument())
        self._expect(TokenKind.RPAREN, "')'")

        if len(args) not in arities:
            allowed = " or ".join(str(n) for n in arities)
            raise self._error(
                f"'{keyword.text}' takes {allowed} arguments, got {len(args)}", keyword
            )
        formal_names = PROV_REC_CLS[rec_type].FORMAL_ATTRIBUTES
        attributes = []
        for attr, token in zip(formal_names, args, strict=False):
            value = self._argument_value(token, attr, bundle)
            if value is not None:
                attributes.append((attr, value))
        record = bundle.new_record(rec_type, identifier, attributes, other_attributes)
        if asserted_type is not None:
            record.add_asserted_type(asserted_type)

    def _argument(self) -> Token:
        if self._current.kind not in _ARGUMENT_KINDS:
            raise self._error(
                f"expected an identifier, a time or '-', found {self._found()}"
            )
        return self._advance()

    def _argument_value(
        self, token: Token, attr: QualifiedName, bundle: ProvBundle
    ) -> Any:
        if token.kind is TokenKind.MARKER:
            return None
        if attr in PROV_ATTRIBUTE_LITERALS:
            if token.kind is not TokenKind.DATETIME:
                raise self._error(
                    f"expected a time for {attr}, found {token.text!r}", token
                )
            value = parse_xsd_datetime(token.value)
            if value is None:
                raise self._error(f"invalid xsd:dateTime {token.text!r}", token)
            return value
        if token.kind is not TokenKind.NAME:
            raise self._error(
                f"expected an identifier for {attr}, found {token.text!r}", token
            )
        return self._resolve(token, bundle)

    def _identifier(self, bundle: ProvBundle) -> QualifiedName:
        return self._resolve(self._expect(TokenKind.NAME, "an identifier"), bundle)

    def _resolve(self, token: Token, bundle: ProvBundle) -> QualifiedName:
        prefix, local = token.value
        if prefix:
            qname = bundle.valid_qualified_name(f"{prefix}:{local}")
            if qname is None:
                raise self._error(
                    f"cannot resolve {token.text!r}: prefix '{prefix}' is not declared",
                    token,
                )
            return qname
        default = bundle.get_default_namespace()
        if default is None and bundle.document is not None:
            default = bundle.document.get_default_namespace()
        if default is None:
            raise self._error(
                f"cannot resolve {token.text!r}: no default namespace declared", token
            )
        return default[local]

    # -- attributes and literals -----------------------------------------------

    def _attributes(self, bundle: ProvBundle) -> list[tuple[QualifiedName, Any]]:
        self._expect(TokenKind.LBRACKET, "'['")
        pairs: list[tuple[QualifiedName, Any]] = []
        if self._current.kind is TokenKind.RBRACKET:
            self._advance()
            return pairs
        while True:
            name = self._expect(TokenKind.NAME, "an attribute name")
            attr = self._resolve(name, bundle)
            self._expect(TokenKind.EQUALS, "'='")
            pairs.append((attr, self._literal(bundle)))
            if self._current.kind is TokenKind.COMMA:
                self._advance()
                continue
            self._expect(TokenKind.RBRACKET, "']'")
            return pairs

    def _literal(self, bundle: ProvBundle) -> Any:
        token = self._current
        if token.kind is TokenKind.STRING:
            self._advance()
            if self._current.kind is TokenKind.LANGTAG:
                return Literal(token.value, langtag=self._advance().value)
            if self._current.kind is TokenKind.TYPED:
                self._advance()
                datatype = self._resolve(
                    self._expect(TokenKind.NAME, "a datatype"), bundle
                )
                return Literal(token.value, datatype)
            return token.value
        if token.kind is TokenKind.INT:
            return self._advance().value
        if token.kind is TokenKind.QNAME_LITERAL:
            self._advance()
            prefix, local = token.value
            text = f"{prefix}:{local}" if prefix else local
            qname = bundle.valid_qualified_name(text)
            # An unresolvable prefix stays an opaque literal, as it does when
            # decoded from PROV-JSON (#257 lock).
            return qname if qname is not None else Literal(text, PROV_QUALIFIEDNAME)
        raise self._error(f"expected a literal value, found {self._found()}")
