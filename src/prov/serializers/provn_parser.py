"""Recursive-descent parser for PROV-N (https://www.w3.org/TR/prov-n/).

The parser reads one token ahead. Every statement opens with a keyword and every
keyword is followed by ``(``, so after one token the parser knows which rule it is in,
and there is no backtracking. Each grammar production is a method (document,
declarations, bundle, statement, expression, attributes, literal).

The expression rule is table-driven, with no method per keyword. ``_KEYWORDS`` maps a
statement keyword's ``(prefix, local)`` to a ``_Rule``: its record type, its legal
argument counts and whether it is an element. ``_classify`` looks the keyword up.
``_arguments`` reads the parenthesised part as a flat list of arguments and an
attribute block. ``_expression`` checks the argument count, maps each position onto
the record class's ``FORMAL_ATTRIBUTES`` in order, with ``-`` markers omitted, and
builds the record. An element takes its identifier first. A relation's optional
identifier is the one place the grammar needs a second token of lookahead, so
``_arguments`` reads the first argument and then checks for ``;``.

Records are built through :meth:`ProvBundle.new_record` with the same arguments the
PROV-JSON deserializer passes, so attribute typing, literal parsing and namespace
registration match every other format.

Profiles share this one parser. ``_PROFILES`` maps each profile name to a ``_Profile``
of two flags, and ``PROFILES`` lists the names:

- ``strict``: ``extensions`` and ``recover`` both off, the Recommendation grammar
  only.
- ``default``: ``extensions`` on. The parser also accepts the bare ``mentionOf``
  keyword that ``prov`` and ProvToolbox write (the Recommendation grammar has no
  Mention production; PROV-Links spells it ``prov:mentionOf``), and the ``-`` marker
  where the grammar has a plain identifier (each rule's smallest ``arities`` entry in
  ``_KEYWORDS``). It also accepts an identifier or an attribute block on a relation
  whose production has neither, a statement after a bundle, a ``default`` declaration
  after a ``prefix`` declaration, and a declaration of ``prov`` or ``xsd`` to its
  predeclared IRI.
- ``lenient``: ``recover`` on as well. A statement that fails to parse, including one
  the model rejects, is skipped and parsing resumes at the next statement. A bundle
  whose identifier the model rejects is skipped too.

Recovery is panic-mode. It records the error and skips tokens to a synchronisation
point. A name followed by ``(`` is one, and so is a structural keyword (``document``,
``endDocument``, ``bundle``, ``endBundle``) not preceded by ``=``, at any bracket
depth. The parser then resumes.

Skipped-statement messages are collected on ``skipped`` rather than warned
here, so :class:`~prov.serializers.provn.ProvNSerializer` can issue the
:class:`~prov.model.ProvWarning` itself with a stack level that points at
the caller of ``deserialize()``, whether the skip happened at document
level or inside a bundle.

Errors are :class:`~prov.serializers.provn.ProvNSyntaxError` and carry the line and
column of the token at fault. ``parse`` tokenises the whole input before it parses a
statement, so a tokenisation error is raised first in every profile and recovery never
applies to it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from prov.constants import (
    _PROV_N_BARE_RELATIONS,
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
    PROV_N_MAP,
    PROV_QUALIFIEDNAME,
    PROV_SPECIALIZATION,
    PROV_START,
    PROV_USAGE,
    XSD,
    XSD_QNAME,
)
from prov.identifier import (
    _PN_PREFIX_NAME,
    Namespace,
    QualifiedName,
    _check_namespace_uri,
)
from prov.model import (
    PROV_REC_CLS,
    Literal,
    ProvBundle,
    ProvDocument,
    ProvException,
    ProvValueError,
    parse_xsd_datetime,
)
from prov.model._values import resolve_name, resolve_pair
from prov.serializers.provn_lexer import (
    ProvNSyntaxError,
    Token,
    TokenKind,
    tokenize,
)

__all__ = ["PROFILES", "ProvNParser"]


@dataclass(frozen=True, slots=True)
class _Profile:
    extensions: bool  # accept the default profile's extensions (see module docstring)
    recover: bool  # skip a statement that fails and resync


_PROFILES = {
    "strict": _Profile(extensions=False, recover=False),
    "default": _Profile(extensions=True, recover=False),
    "lenient": _Profile(extensions=True, recover=True),
}
PROFILES = tuple(_PROFILES)


@dataclass(frozen=True, slots=True)
class _Rule:
    record_type: QualifiedName
    arities: tuple[int, ...]  # allowed argument counts after the identifier, if any
    element: bool  # an element takes its identifier first, a relation an optional 'id;'


# An attribute block's pairs: name, value and the token that names it.
_AttributeBlock = list[tuple[QualifiedName, Any, Token]]

# (prefix, local) of a statement keyword -> its rule. A relation's compact form
# (no ';') lists exactly its required identifiers, so its smallest arity is the
# number of leading arguments the strict profile refuses '-' in (#257). Bare
# 'mentionOf' is not a key, because the profile decides it.
_KEYWORDS: dict[tuple[str, str], _Rule] = {
    ("", "entity"): _Rule(PROV_ENTITY, (0,), element=True),
    ("", "activity"): _Rule(PROV_ACTIVITY, (0, 2), element=True),
    ("", "agent"): _Rule(PROV_AGENT, (0,), element=True),
    ("", "wasGeneratedBy"): _Rule(PROV_GENERATION, (1, 3), element=False),
    ("", "used"): _Rule(PROV_USAGE, (1, 3), element=False),
    ("", "wasInvalidatedBy"): _Rule(PROV_INVALIDATION, (1, 3), element=False),
    ("", "wasStartedBy"): _Rule(PROV_START, (1, 4), element=False),
    ("", "wasEndedBy"): _Rule(PROV_END, (1, 4), element=False),
    ("", "wasInformedBy"): _Rule(PROV_COMMUNICATION, (2,), element=False),
    ("", "wasAttributedTo"): _Rule(PROV_ATTRIBUTION, (2,), element=False),
    ("", "wasAssociatedWith"): _Rule(PROV_ASSOCIATION, (1, 3), element=False),
    ("", "actedOnBehalfOf"): _Rule(PROV_DELEGATION, (2, 3), element=False),
    ("", "wasDerivedFrom"): _Rule(PROV_DERIVATION, (2, 5), element=False),
    ("", "wasInfluencedBy"): _Rule(PROV_INFLUENCE, (2,), element=False),
    ("", "alternateOf"): _Rule(PROV_ALTERNATE, (2,), element=False),
    ("", "specializationOf"): _Rule(PROV_SPECIALIZATION, (2,), element=False),
    ("", "hadMember"): _Rule(PROV_MEMBERSHIP, (2,), element=False),
    ("prov", "mentionOf"): _Rule(PROV_MENTION, (3,), element=False),
}
_STRUCTURAL = frozenset({"document", "endDocument", "bundle", "endBundle"})
_ARGUMENT_KINDS = (TokenKind.NAME, TokenKind.MARKER, TokenKind.DATETIME)

# PROV-N keywords of the relations that take neither an identifier nor an
# attribute block (productions 24 to 26).
_BARE_RELATIONS = frozenset(PROV_N_MAP[t] for t in _PROV_N_BARE_RELATIONS)

# PROV-N predeclares these two prefixes; ``xsi`` is an ordinary prefix.
_RESERVED_PREFIXES: dict[str, Namespace] = {"prov": PROV, "xsd": XSD}


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

    # self._tokens[self._pos] once parse() has run; set by parse() and _advance().
    _current: Token

    def __init__(self, text: str, profile: str = "default"):
        if profile not in PROFILES:
            raise ValueError(f"profile must be one of {PROFILES}, got {profile!r}")
        self.profile = profile
        self._profile = _PROFILES[profile]
        self.skipped: list[str] = []
        self._text = text
        self._tokens: list[Token] = []
        self._pos = 0
        self._previous_kind: TokenKind | None = None  # last consumed token's kind

    # -- token helpers -----------------------------------------------------

    def _peek(self) -> Token:
        index = min(self._pos + 1, len(self._tokens) - 1)
        return self._tokens[index]

    def _advance(self) -> Token:
        token = self._current
        self._previous_kind = token.kind
        if self._pos < len(self._tokens) - 1:
            self._pos += 1
            self._current = self._tokens[self._pos]
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

    def _digit_run_as_name(self) -> Token | None:
        """Re-kind the current token from INT to NAME if it's an unsigned
        digit run ([53] PN_LOCAL allows a leading digit, but not an
        unescaped '-'). The lexer tokenises without regard to grammar
        position, so it always reads a digit run as INT; a signed INT
        ('-4567') is not a valid local name and is left alone. Returns
        ``None``, without advancing, when the current token doesn't match."""
        if self._current.kind is not TokenKind.INT or self._current.text.startswith(
            "-"
        ):
            return None
        token = self._advance()
        return Token(
            TokenKind.NAME, token.text, ("", token.text), token.line, token.column
        )

    def _identifier_token(self, *, inside_parens: bool = True) -> Token:
        """An identifier position also accepts a bare, all-digit local name;
        see :meth:`_digit_run_as_name`. Inside a statement's parentheses
        (``inside_parens``, the default), also guards against swallowing a
        structural keyword; see :meth:`_reject_unclosed_structural_keyword`.
        A bundle's own header identifier (``bundle <id>``) is not inside
        parentheses, so :meth:`_bundle` passes ``inside_parens=False`` and
        accepts a bare keyword-shaped name (e.g. a bundle literally named
        ``bundle``) unconditionally. Anything else falls through to the
        usual NAME-expected error."""
        digit_run = self._digit_run_as_name()
        if digit_run is not None:
            return digit_run
        if inside_parens:
            self._reject_unclosed_structural_keyword()
        return self._expect(TokenKind.NAME, "an identifier")

    def _reject_unclosed_structural_keyword(self) -> None:
        """Refuse a bare structural keyword as an identifier or argument
        unless it is immediately followed by ',', ')' or ';' -- the only
        tokens that follow a real identifier inside a statement's
        parentheses. Anything else means a statement left open by a
        missing ')'/']' has read straight through a following 'bundle',
        'endBundle' or 'endDocument' as if it were data; raising here
        without consuming the token lets lenient resync (and, outside
        lenient, the enclosing loop) still find it.
        """
        current = self._current
        if current.kind is not TokenKind.NAME:
            return
        prefix, local = current.value
        if prefix or local not in _STRUCTURAL:
            return
        if self._peek().kind in (
            TokenKind.COMMA,
            TokenKind.RPAREN,
            TokenKind.SEMICOLON,
        ):
            return
        raise self._error(f"expected an identifier, found {self._found()}")

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
        self._current = self._tokens[0]
        document = ProvDocument()
        self._expect_keyword("document")
        namespaces, default = self._declarations()
        self._apply_declarations(document, namespaces, default)
        after_bundle = False
        while not self._at_keyword("endDocument"):
            if self._current.kind is TokenKind.EOF:
                raise self._error("expected 'endDocument', found end of input")
            if self._at_keyword("bundle"):
                self._bundle(document)
                after_bundle = True
            else:
                # Production 1 puts every expression before the first bundle.
                if after_bundle and not self._profile.extensions:
                    raise self._error(
                        "a statement follows a bundle, which the strict profile"
                        " does not allow"
                    )
                self._statement(document)
        self._advance()
        if self._current.kind is not TokenKind.EOF:
            raise self._error("unexpected content after 'endDocument'")
        return document

    def _declarations(self) -> tuple[list[Namespace], str | None]:
        """Consume 'prefix'/'default' declarations without committing them.

        Used both by :meth:`parse` (applied immediately via
        :meth:`_apply_declarations`) and by :meth:`_bundle` (which needs the
        bundle's own declarations before the bundle exists, to resolve its
        identifier against them).

        Raises at a repeated default, at a prefix that is not a PN_PREFIX, at
        an IRI that is empty or starts with ``@``, and under the strict profile
        at a default that follows a prefix and at a declaration of prov or xsd.
        """
        namespaces: list[Namespace] = []
        default: str | None = None
        seen: set[str] = set()
        while True:
            if self._at_keyword("prefix"):
                self._advance()
                name = self._expect(TokenKind.NAME, "a prefix")
                prefix, local = name.value
                if prefix:
                    raise self._error(f"expected a prefix, found {name.text!r}", name)
                if local in seen:
                    raise self._error(
                        f"prefix '{local}' is declared twice in this scope", name
                    )
                iri = self._namespace_iri()
                self._check_reserved_prefix(local, iri.value, name)
                if not _PN_PREFIX_NAME.fullmatch(local):
                    raise self._error(
                        f"'{local}' is not a PROV-N prefix name, so no qualified"
                        " name can use it",
                        name,
                    )
                namespaces.append(Namespace(local, iri.value))
                seen.add(local)
            elif self._at_keyword("default"):
                keyword = self._advance()
                iri = self._namespace_iri()
                if default is not None:
                    raise self._error(
                        "'default' is declared twice in this scope", keyword
                    )
                if namespaces and not self._profile.extensions:
                    raise self._error(
                        "'default' follows a 'prefix' declaration, which the"
                        " strict profile does not allow",
                        keyword,
                    )
                default = iri.value
            else:
                return namespaces, default

    def _namespace_iri(self) -> Token:
        """Consume the IRI of a declaration.

        An empty IRI is refused here with its own sentence. Any other IRI the
        model refuses is a positioned syntax error carrying the model's error
        as its cause.
        """
        iri = self._expect(TokenKind.IRI, "an IRI in angle brackets")
        if not iri.value:
            raise self._error("a namespace IRI cannot be empty", iri)
        try:
            _check_namespace_uri(iri.value)
        except ProvValueError as exc:
            raise self._error(str(exc), iri) from exc
        return iri

    def _check_reserved_prefix(self, prefix: str, uri: str, token: Token) -> None:
        reserved = _RESERVED_PREFIXES.get(prefix)
        if reserved is None:
            return
        if reserved.uri != uri:
            raise self._error(
                f"prefix '{prefix}' is reserved for <{reserved.uri}> and cannot"
                " be redeclared",
                token,
            )
        if not self._profile.extensions:
            raise self._error(
                f"prefix '{prefix}' is predeclared, and the strict profile does"
                " not allow declaring it",
                token,
            )

    def _apply_declarations(
        self, target: ProvBundle, namespaces: list[Namespace], default: str | None
    ) -> None:
        for namespace in namespaces:
            target.add_namespace(namespace)
        if default is not None:
            target.set_default_namespace(default)

    def _bundle(self, document: ProvDocument) -> None:
        self._advance()  # 'bundle'
        id_token = self._identifier_token(inside_parens=False)
        namespaces, default = self._declarations()
        # PROV-N 3.1.3: the bundle identifier resolves with the bundle's own
        # declarations first, then the document's.
        bundle = ProvBundle(document=document)
        self._apply_declarations(bundle, namespaces, default)
        try:
            document.add_bundle(bundle, self._resolve(id_token, bundle))
        except ProvNSyntaxError:
            raise
        except ProvException as exc:
            error = ProvNSyntaxError(str(exc), id_token.line, id_token.column)
            if not self._profile.recover:
                raise error from exc
            error.__cause__ = exc
            self.skipped.append(f"PROV-N bundle skipped: {error}")
            self._skip_bundle_body()
            return
        while not self._at_keyword("endBundle"):
            if self._current.kind is TokenKind.EOF:
                raise self._error("expected 'endBundle', found end of input")
            if self._at_keyword("bundle"):
                raise self._error("a bundle cannot contain a bundle")
            self._statement(bundle)
        self._advance()

    def _skip_bundle_body(self) -> None:
        """Consume everything up to and including the next 'endBundle'."""
        while not self._at_keyword("endBundle"):
            if self._current.kind is TokenKind.EOF:
                raise self._error("expected 'endBundle', found end of input")
            self._advance()
        self._advance()

    def _statement(self, bundle: ProvBundle) -> None:
        start = self._current
        try:
            self._expression(bundle)
        except ProvNSyntaxError as error:
            self._skip_or_raise(error)
        except (ProvException, ValueError, OverflowError) as exc:
            # A model rejection (e.g. from new_record()) is reported as a
            # positioned syntax error and, under lenient, skipped.
            wrapped = ProvNSyntaxError(str(exc), start.line, start.column)
            wrapped.__cause__ = exc
            self._skip_or_raise(wrapped)

    def _skip_or_raise(self, error: ProvNSyntaxError) -> None:
        if not self._profile.recover:
            raise error
        self.skipped.append(f"PROV-N statement skipped: {error}")
        self._resync()

    def _looks_like_statement_start(self) -> bool:
        """A NAME immediately followed by '(' opens a statement.

        No production puts '(' after a name inside a statement body
        (arguments and attribute values are followed by ',', ']' or ')'),
        so the pair marks a boundary whatever the name is: a keyword, an
        unknown keyword or a prefixed extensibility expression. Testing the
        name against the keyword tables instead would run a skip through
        every following statement the tables do not know, reporting a run
        of bad statements as one.
        """
        return self._peek().kind is TokenKind.LPAREN

    def _resync(self) -> None:
        """Skip to the next statement boundary.

        A name immediately followed by ``(`` is a boundary at any bracket
        depth, because it is never legal inside a statement body.

        A bare structural keyword (``document``, ``bundle``, ...) is not
        followed by ``(``, so it cannot be told apart this way from the
        same word used as an ordinary attribute value (e.g.
        ``[ex:k=bundle]``); that case is instead gated on whether the token
        before it is ``=``, since only an attribute value follows one.
        """
        while self._current.kind is not TokenKind.EOF:
            token = self._current
            if token.kind is TokenKind.NAME:
                prefix, local = token.value
                if not prefix and local in _STRUCTURAL:
                    # A structural keyword is a boundary unless it is an
                    # attribute value ([ex:k=bundle]), which only follows '='.
                    if self._previous_kind is not TokenKind.EQUALS:
                        return
                elif self._looks_like_statement_start():
                    return
            self._advance()

    # -- expressions -------------------------------------------------------------

    def _classify(self, token: Token) -> _Rule:
        """Return the rule for a statement keyword token."""
        prefix, local = token.value
        rule = _KEYWORDS.get(token.value)
        if rule is not None:
            return rule
        if prefix:
            raise self._error(
                f"extensibility expression '{token.text}(...)' is not supported", token
            )
        if local == "mentionOf":
            if self._profile.extensions:
                return _KEYWORDS[("prov", "mentionOf")]
            raise self._error(
                "unknown statement keyword 'mentionOf' under the strict profile: "
                "write 'prov:mentionOf', or parse with profile='default' to accept "
                "the bare keyword",
                token,
            )
        raise self._error(f"unknown statement keyword '{local}'", token)

    def _expression(self, bundle: ProvBundle) -> None:
        """Parse one statement, production ``expression``, and add its record."""
        keyword = self._expect(TokenKind.NAME, "a statement keyword")
        rule = self._classify(keyword)
        identifier, args, attribute_block = self._arguments(keyword, rule, bundle)

        if len(args) not in rule.arities:
            allowed = " or ".join(str(n) for n in rule.arities)
            raise self._error(
                f"'{keyword.text}' takes {allowed} arguments, got {len(args)}", keyword
            )
        self._check_strict_required_positions(keyword, rule, args)
        formal_names = PROV_REC_CLS[rule.record_type].FORMAL_ATTRIBUTES
        attributes = []
        for attr, token in zip(formal_names, args, strict=False):
            value = self._argument_value(token, attr, bundle)
            if value is not None:
                attributes.append((attr, value))
        self._check_formal_attributes(keyword, formal_names, attribute_block)
        other_attributes = [(name, value) for name, value, _ in attribute_block]
        bundle.new_record(rule.record_type, identifier, attributes, other_attributes)

    def _arguments(
        self, keyword: Token, rule: _Rule, bundle: ProvBundle
    ) -> tuple[QualifiedName | None, list[Token], _AttributeBlock]:
        """Read the parenthesised part of production ``expression``.

        Return the identifier, the positional arguments and the attribute block.
        """
        self._expect(TokenKind.LPAREN)
        identifier: QualifiedName | None = None
        args: list[Token] = []
        if rule.element:
            id_token = self._identifier_token()
            identifier = self._resolve(id_token, bundle)
        else:
            first = self._argument()
            if self._current.kind is TokenKind.SEMICOLON:
                self._check_strict_bare_relation(keyword, first, "an identifier")
                if first.kind is TokenKind.MARKER:
                    identifier = None
                elif first.kind is TokenKind.NAME:
                    identifier = self._resolve(first, bundle)
                else:
                    raise self._error("expected an identifier before ';'", first)
                self._advance()
                args.append(self._argument())
            else:
                args.append(first)
        attribute_block: _AttributeBlock = []
        separator = self._current.kind
        while separator is TokenKind.COMMA:
            self._advance()
            if self._current.kind is TokenKind.LBRACKET:
                self._check_strict_bare_relation(
                    keyword, self._current, "an attribute block"
                )
                attribute_block = self._attributes(bundle)
                break
            args.append(self._argument())
            separator = self._current.kind
        self._expect(TokenKind.RPAREN)
        return identifier, args, attribute_block

    def _check_strict_bare_relation(
        self, keyword: Token, token: Token, what: str
    ) -> None:
        """Under ``strict``, reject an identifier or an attribute block on a
        relation whose production has neither (productions 24 to 26)."""
        if not self._profile.extensions and keyword.value[1] in _BARE_RELATIONS:
            raise self._error(
                f"'{keyword.text}' has {what}, which the strict profile does not allow",
                token,
            )

    def _check_formal_attributes(
        self,
        keyword: Token,
        formal_names: tuple[QualifiedName, ...],
        attribute_block: _AttributeBlock,
    ) -> None:
        """Reject an attribute named after one of the statement's own
        arguments, which PROV-N gives only by position (#523)."""
        for name, _, token in attribute_block:
            if name in formal_names:
                raise self._error(
                    f"'{token.text}' names the '{name.localpart}' argument of"
                    f" '{keyword.text}', which PROV-N gives only by position",
                    token,
                )

    def _check_strict_required_positions(
        self, keyword: Token, rule: _Rule, args: list[Token]
    ) -> None:
        """Under ``strict``, reject '-' where the grammar has a plain
        identifier (no ``OrMarker``); ``default``/``lenient`` keep accepting
        it there, matching the model's scruffy-statement policy."""
        if self._profile.extensions:
            return
        required = min(rule.arities)
        for index, arg in enumerate(args[:required]):
            if arg.kind is TokenKind.MARKER:
                raise self._error(
                    f"'{keyword.text}' requires an identifier at argument"
                    f" {index + 1}, found '-'",
                    arg,
                )

    def _argument(self) -> Token:
        # A relation argument is always an identifier, a time or '-', never
        # a literal, so an unsigned INT token here is a bare local name;
        # see _digit_run_as_name().
        digit_run = self._digit_run_as_name()
        if digit_run is not None:
            return digit_run
        if self._current.kind not in _ARGUMENT_KINDS:
            raise self._error(
                f"expected an identifier, a time or '-', found {self._found()}"
            )
        self._reject_unclosed_structural_keyword()
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

    def _resolve(self, token: Token, bundle: ProvBundle) -> QualifiedName:
        # A name resolves by its prefix in scope, never by compacting an IRI
        # (#553, #599), so http://example.org/e is the undeclared prefix 'http'.
        prefix, local = token.value
        qname = bundle._lookup(prefix, local)
        if qname is None:
            why = (
                f"prefix '{prefix}' is not declared"
                if prefix
                else "no default namespace declared"
            )
            raise self._error(f"cannot resolve {token.text!r}: {why}", token)
        return qname

    # -- attributes and literals -----------------------------------------------

    def _attributes(self, bundle: ProvBundle) -> _AttributeBlock:
        """Parse an attribute block into (name, value, name token) triples."""
        self._expect(TokenKind.LBRACKET)
        pairs: _AttributeBlock = []
        if self._current.kind is TokenKind.RBRACKET:
            self._advance()
            return pairs
        while True:
            name = self._digit_run_as_name() or self._expect(
                TokenKind.NAME, "an attribute name"
            )
            attr = self._resolve(name, bundle)
            self._expect(TokenKind.EQUALS)
            pairs.append((attr, self._literal(bundle), name))
            if self._current.kind is TokenKind.COMMA:
                self._advance()
                continue
            self._expect(TokenKind.RBRACKET)
            return pairs

    def _literal(self, bundle: ProvBundle) -> Any:
        token = self._current
        if token.kind is TokenKind.STRING:
            self._advance()
            if self._current.kind is TokenKind.LANGTAG:
                return Literal(token.value, langtag=self._advance().value)
            if self._current.kind is TokenKind.TYPED:
                self._advance()
                datatype_token = self._digit_run_as_name() or self._expect(
                    TokenKind.NAME, "a datatype"
                )
                datatype = self._resolve(datatype_token, bundle)
                if datatype in (PROV_QUALIFIEDNAME, XSD_QNAME):
                    return self._resolve_name_value(token, bundle)
                return Literal(token.value, datatype)
            return token.value
        if token.kind is TokenKind.INT:
            return self._advance().value
        if token.kind is TokenKind.QNAME_LITERAL:
            self._advance()
            return self._resolve_name_value(token, bundle)
        raise self._error(f"expected a literal value, found {self._found()}")

    def _resolve_name_value(self, token: Token, bundle: ProvBundle) -> QualifiedName:
        """The qualified-name value at ``token``: a lexed pair for a
        ``'ex:x'`` literal, a string for ``"ex:x" %% xsd:QName``; rejected
        at the token when it does not resolve by its prefix (#516, #553)."""
        text = token.value
        if not isinstance(text, tuple):
            name = resolve_name(bundle, text)
            if isinstance(name, str):
                raise self._error(name, token)
            return name
        prefix, local = text
        if not prefix and ":" in local:
            # An escaped colon has no text form the resolver would split
            # correctly, so the token itself reports the failure.
            return self._resolve(token, bundle)
        qname = resolve_pair(bundle, prefix, local)
        if isinstance(qname, str):
            raise self._error(qname, token)
        return qname
