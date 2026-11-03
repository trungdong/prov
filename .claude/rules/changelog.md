# Changelog entries

These rules govern every entry in `HISTORY.md`. The maintainer owns `HISTORY.md`, so an
entry goes in the maintainer's own pull requests; a contributor's pull request adds none,
and the maintainer writes its entry.

- Write one entry per change a user can see, in the pull request that makes it, under the
  unreleased version's fixed headings: Breaking changes, New features, Fixes and Project.
  Breaking changes comes first. It holds everything a reader of the previous release may
  have to act on: input now rejected, behaviour that changed with or without a prior
  warning, and output that changed shape.
- State the new behaviour. When a reader must change code, say what to write instead, and
  only then give the old behaviour, as one clause ("where 3.2.3 read it as ...").
- Keep an entry to one or two sentences, under about 40 words. Anything longer belongs on
  the page that owns the topic (the upgrade guide, the reference or the conformance
  page), and the entry links that page.
- End the entry with one issue or pull request link.
- Write no entry for a refactor, a test, CI, tooling, a docs-only change, a change too minor
  for a user to notice, or one that changes no behaviour; the milestone link covers them. A
  Project entry is one line and only for something a user meets, such as a deprecation.
- Write an entry once. A later pull request adds its own entry and never grows an earlier
  one. The pre-release documentation audit may rewrite the unreleased section as a whole.
- At release time, the release pull request adds an opening summary of two to four
  sentences (what kind of release it is and who has to act) and a short list of the
  changes that require action, one line each, linking the how-to. Nothing else is added
  at release time.
- When entries share a subject, such as the command-line tools or a set of deprecations,
  group them under one parent bullet with one sub-bullet each. Each sub-bullet keeps its
  own link.
