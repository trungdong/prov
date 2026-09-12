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
- ``lenient``: as ``default``; a statement that fails to parse, including
  one the model rejects, is skipped and parsing resumes at the next
  statement. Tokenisation errors are fatal in every profile.

Skipped-statement messages are collected on ``skipped`` rather than warned
here, so :class:`~prov.serializers.provn.ProvNSerializer` can issue the
:class:`~prov.model.ProvWarning` itself with a stack level that points at
the caller of ``deserialize()``, whether the skip happened at document
level or inside a bundle.
"""

from __future__ import annotations

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
    DEFAULT_NAMESPACES,
    PROV_REC_CLS,
    Literal,
    ProvBundle,
    ProvDocument,
    ProvException,
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

# keyword -> number of leading arguments (after any 'id;') that the
# Recommendation's grammar makes a plain identifier, not an identifierOrMarker;
# '-' there is only ever accepted under the default/lenient extensions,
# matching the model's scruffy-statement policy (#257).
_STRICT_REQUIRED_LEADING: dict[str, int] = {
    "wasGeneratedBy": 1,
    "used": 1,
    "wasInvalidatedBy": 1,
    "wasStartedBy": 1,
    "wasEndedBy": 1,
    "wasAssociatedWith": 1,
    "wasInformedBy": 2,
    "wasAttributedTo": 2,
    "wasInfluencedBy": 2,
    "alternateOf": 2,
    "specializationOf": 2,
    "hadMember": 2,
    "actedOnBehalfOf": 2,
    "wasDerivedFrom": 2,
    "mentionOf": 3,
}


class ProvNParser:
    """Parse one PROV-N document.

    Args:
        text: The PROV-N source.
        profile: One of :data:`PROFILES`.

    Attributes:
        skipped: Messages for the statements the ``lenient`` profile
            skipped, in source order; empty for every other profile. Read
            after :meth:`parse` returns.

    Raises:
        ValueError: If ``profile`` is not one of :data:`PROFILES`.
    """

    def __init__(self, text: str, profile: str = "default"):
        if profile not in PROFILES:
            raise ValueError(f"profile must be one of {PROFILES}, got {profile!r}")
        self.profile = profile
        self.skipped: list[str] = []
        self._text = text
        self._tokens: list[Token] = []
        self._pos = 0
        self._depth = 0

    # -- token helpers -----------------------------------------------------

    @property
    def _current(self) -> Token:
        return self._tokens[self._pos]

    def _peek(self) -> Token:
        index = min(self._pos + 1, len(self._tokens) - 1)
        return self._tokens[index]

    def _advance(self) -> Token:
        token = self._tokens[self._pos]
        if token.kind in (TokenKind.LPAREN, TokenKind.LBRACKET):
            self._depth += 1
        elif token.kind in (TokenKind.RPAREN, TokenKind.RBRACKET):
            self._depth = max(0, self._depth - 1)
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
        self._depth = 0
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

    def _parse_declarations(self) -> tuple[list[Namespace], str | None]:
        """Consume 'prefix'/'default' declarations without committing them.

        Used both by :meth:`_declarations` (applied immediately) and by
        :meth:`_bundle` (which needs the bundle's own declarations before
        the bundle exists, to resolve its identifier against them).
        """
        namespaces: list[Namespace] = []
        default: str | None = None
        while True:
            if self._at_keyword("prefix"):
                self._advance()
                name = self._expect(TokenKind.NAME, "a prefix")
                prefix, local = name.value
                if prefix:
                    raise self._error(f"expected a prefix, found {name.text!r}", name)
                iri = self._expect(TokenKind.IRI, "an IRI in angle brackets")
                self._check_reserved_prefix(local, iri.value, name)
                namespaces.append(Namespace(local, iri.value))
            elif self._at_keyword("default"):
                self._advance()
                iri = self._expect(TokenKind.IRI, "an IRI in angle brackets")
                default = iri.value
            else:
                return namespaces, default

    def _check_reserved_prefix(self, prefix: str, uri: str, token: Token) -> None:
        builtin = DEFAULT_NAMESPACES.get(prefix)
        if builtin is not None and builtin.uri != uri:
            raise self._error(
                f"prefix '{prefix}' is reserved for <{builtin.uri}> and cannot"
                " be redeclared",
                token,
            )

    def _apply_declarations(
        self, target: ProvBundle, namespaces: list[Namespace], default: str | None
    ) -> None:
        for namespace in namespaces:
            target.add_namespace(namespace)
        if default is not None:
            target.set_default_namespace(default)

    def _declarations(self, bundle: ProvBundle) -> None:
        namespaces, default = self._parse_declarations()
        self._apply_declarations(bundle, namespaces, default)

    def _bundle(self, document: ProvDocument) -> None:
        self._advance()  # 'bundle'
        id_token = self._expect(TokenKind.NAME, "an identifier")
        namespaces, default = self._parse_declarations()
        # PROV-N 3.1.3: the bundle identifier is resolved with the bundle's
        # own declarations. Only take the bundle-based resolution path when
        # the identifier actually needs one of those declarations (a
        # bundle-local prefix, or a bare name and the bundle sets its own
        # default) -- document.add_bundle() then normalises the identifier
        # against the bundle's own namespaces, not the document's, so a
        # bundle-local prefix is never registered on the document. Otherwise
        # resolve against the document directly, exactly as a bundle with no
        # declarations of its own would, so a document-level prefix used for
        # the identifier is not redundantly copied onto the bundle too.
        prefix, _ = id_token.value
        if (prefix and prefix in {ns.prefix for ns in namespaces}) or (
            not prefix and default is not None
        ):
            bundle = ProvBundle(document=document)
            self._apply_declarations(bundle, namespaces, default)
            identifier = self._resolve(id_token, bundle)
            document.add_bundle(bundle, identifier)
        else:
            identifier = self._resolve(id_token, document)
            bundle = document.bundle(identifier)
            self._apply_declarations(bundle, namespaces, default)
        while not self._at_keyword("endBundle"):
            if self._current.kind is TokenKind.EOF:
                raise self._error("expected 'endBundle', found end of input")
            if self._at_keyword("bundle"):
                raise self._error("a bundle cannot contain a bundle")
            self._statement(bundle)
        self._advance()

    def _statement(self, bundle: ProvBundle) -> None:
        start = self._current
        start_depth = self._depth
        try:
            self._expression(bundle)
        except (ProvException, ValueError, OverflowError) as exc:
            # A model rejection (e.g. from new_record()) or a bad typed
            # literal (e.g. int("abc") inside parse_xsd_types()) is not
            # already positioned, so wrap it the same way a grammar error
            # already is; every kind then gets the same lenient skip-or-raise.
            error = (
                exc
                if isinstance(exc, ProvNSyntaxError)
                else ProvNSyntaxError(str(exc), start.line, start.column)
            )
            if self.profile != "lenient":
                if error is exc:
                    raise
                raise error from exc
            self.skipped.append(f"PROV-N statement skipped: {error}")
            self._resync(start_depth)

    def _looks_like_statement_start(self, token: Token) -> bool:
        prefix, local = token.value
        if not prefix and local in _STRUCTURAL:
            return True
        is_candidate = (
            not prefix
            and (
                local in _ELEMENTS
                or local in _RELATIONS
                or local in _SHORTHAND
                or local == "mentionOf"
            )
        ) or (prefix, local) == ("prov", "mentionOf")
        # A bare NAME that merely spells a keyword (e.g. an attribute name or
        # value) is not a new statement unless it is actually followed by
        # '(', as every real keyword use is.
        return is_candidate and self._peek().kind is TokenKind.LPAREN

    def _resync(self, start_depth: int) -> None:
        """Skip to the next statement boundary at the statement's own depth."""
        while self._current.kind is not TokenKind.EOF:
            token = self._current
            if (
                self._depth <= start_depth
                and token.kind is TokenKind.NAME
                and self._looks_like_statement_start(token)
            ):
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
        identifier: QualifiedName | str | None = None
        args: list[Token] = []
        if is_element:
            id_token = self._expect(TokenKind.NAME, "an identifier")
            identifier = self._identifier_text(id_token, bundle)
        else:
            first = self._argument()
            if self._current.kind is TokenKind.SEMICOLON:
                if first.kind is TokenKind.MARKER:
                    identifier = None
                elif first.kind is TokenKind.NAME:
                    identifier = self._identifier_text(first, bundle)
                else:
                    raise self._error("expected an identifier before ';'", first)
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
        _, local = keyword.value
        self._check_strict_required_positions(keyword, local, args)
        formal_names = PROV_REC_CLS[rec_type].FORMAL_ATTRIBUTES
        attributes = []
        for attr, token in zip(formal_names, args, strict=False):
            value = self._argument_value(token, attr, bundle)
            if value is not None:
                attributes.append((attr, value))
        record = bundle.new_record(rec_type, identifier, attributes, other_attributes)
        if asserted_type is not None:
            record.add_asserted_type(asserted_type)

    def _check_strict_required_positions(
        self, keyword: Token, local: str, args: list[Token]
    ) -> None:
        """Under ``strict``, reject '-' where the grammar has a plain
        identifier (no ``OrMarker``); ``default``/``lenient`` keep accepting
        it there, matching the model's scruffy-statement policy (#257)."""
        if self.profile != "strict":
            return
        required = _STRICT_REQUIRED_LEADING.get(local, 0)
        for index, arg in enumerate(args[:required]):
            if arg.kind is TokenKind.MARKER:
                raise self._error(
                    f"'{keyword.text}' requires an identifier at argument"
                    f" {index + 1}, found '-'",
                    arg,
                )

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

    def _identifier_text(self, token: Token, bundle: ProvBundle) -> QualifiedName | str:
        """Validate an identifier and return its literal text where possible,
        rather than a resolved ``QualifiedName``.

        ``new_record()``/``document.bundle()`` call ``valid_qualified_name()``
        on the identifier themselves; handing them an already-resolved
        ``QualifiedName`` for a name delegated from a parent's default
        namespace makes that call reconcile it onto this bundle as its OWN
        default namespace, which the plain-string path does not do.
        """
        resolved = self._resolve(token, bundle)
        prefix, local = token.value
        if not prefix and ":" in local:
            # An escaped colon in a bare local part can't be turned back
            # into text without looking like a (wrong) prefixed name, so
            # this one shape is passed on already resolved -- accepted,
            # documented limitation: inside a bundle with no default of its
            # own, this resolves against the enclosing document's default,
            # and passing the already-resolved QualifiedName on to
            # new_record() then makes the bundle adopt that default as its
            # own (visible as an extra 'default <...>' line inside the
            # bundle on re-serialisation), unlike a plain bare name, which
            # goes through the string path and is not cached this way.
            return resolved
        return f"{prefix}:{local}" if prefix else local

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
        if ":" in local:
            # An escaped colon inside a bare (unprefixed) local part would be
            # mis-split by valid_qualified_name()'s string-based prefix
            # lookup, so this one shape still resolves against the default
            # namespace directly.
            default = bundle.get_default_namespace()
            if default is None and bundle.document is not None:
                default = bundle.document.get_default_namespace()
            if default is None:
                raise self._error(
                    f"cannot resolve {token.text!r}: no default namespace declared",
                    token,
                )
            return default[local]
        qname = bundle.valid_qualified_name(local)
        if qname is None:
            raise self._error(
                f"cannot resolve {token.text!r}: no default namespace declared", token
            )
        return qname

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
