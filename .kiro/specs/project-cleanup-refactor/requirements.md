# Requirements Document

## Introduction

This feature is a behavior-preserving cleanup refactor of the Silco codebase. The goal is to improve code clarity, consistency, and maintainability without changing any externally observable behavior or public usage. The refactor MUST keep every currently importable name, method signature, alias, plugin registration, rendered output, CLI entry point, and notebook integration intact. Improvements target dead code removal, deduplication of registrations and helpers, consistent module conventions, tightened public re-exports, and clearer naming and docstrings.

## Glossary

- **Silco**: The Python package distributed under the name `silco` (root package directory `silco/`).
- **Public_API**: The set of names re-exported by `silco/__init__.py`, `silco/core/__init__.py`, `silco/core/models/__init__.py`, `silco/plugins/__init__.py`, and the public symbols of `silco.plugins.ipython` and `silco.plugins.pdf` as they exist on the pre-refactor `main` branch.
- **Public_Method**: Any method on `silco.Diagram` not prefixed with a single underscore, plus the documented dunder hooks `_repr_svg_` and `_repr_html_`, plus the chainable aliases `node`, `connect`, `flow`, `group`.
- **Renderer_Output**: The string, bytes, or object returned by `Diagram.to_svg`, `Diagram.to_mermaid`, `Diagram.to_html`, `Diagram.to_pdf`, `Diagram.save_pdf`, and `Diagram.render` for a given diagram and option set.
- **SVG_Output**: The string returned by `Diagram.to_svg(**options)` for any valid options.
- **Mermaid_Output**: The string returned by `Diagram.to_mermaid()`.
- **Plugin_Registry**: The `kernel` singleton from `silco.core.kernel.kernel` and the names returned by `kernel.names(category)` for each category in `kernel.categories()`.
- **Built_in_Plugin**: A plugin auto-registered as a side effect of importing `silco.core.renderers` or `silco.plugins.renderers` (layouts `dag` and `grid`; renderers `svg` and `mermaid`; styles `modern` and `uml`).
- **Optional_Plugin**: A plugin registered through entry points or namespace discovery (`silco.plugins.ipython`, `silco.plugins.pdf`).
- **Cleanup_Refactor**: The set of code changes made under this spec.
- **Behavior_Equivalent**: Two outputs are behavior-equivalent if they are byte-identical OR they differ only by a documented, deterministic normalization (for example whitespace inside SVG attribute padding) that does not change meaning for any consumer.
- **Tutorial_Notebook**: The file `tutorial.ipynb` at the repository root.
- **CLI_Entry**: The script `main.py` at the repository root and its `main()` function.

## Requirements

### Requirement 1: Preserve top-level public API surface

**User Story:** As a Silco user, I want every name I currently import from the top-level package to keep working, so that my existing code does not break after the refactor.

#### Acceptance Criteria

1. THE Silco SHALL expose `Canvas`, `Diagram`, `Edge`, `Element`, `Flow`, `Group`, `Node`, `PluginInfo`, `RenderConfig`, `diagram`, and `kernel` as importable attributes of the `silco` package after the Cleanup_Refactor.
2. WHEN a user evaluates `from silco import diagram, kernel`, THE Silco SHALL bind `diagram` to the same callable and `kernel` to the same singleton instance class as before the Cleanup_Refactor.
3. THE Silco SHALL keep the identifiers `Canvas`, `Diagram`, `Edge`, `Element`, `Flow`, `Group`, `Layout`, `Node`, `NodeKind`, `PLUGIN_CATEGORIES`, `PluginCategory`, `PluginInfo`, `PositionedNode`, `RenderConfig`, `SilcoKernel`, `diagram`, and `kernel` importable from `silco.core` after the Cleanup_Refactor.
4. THE Silco SHALL keep `Edge`, `Flow`, `Group`, `Node`, and `NodeKind` importable from `silco.core.models` after the Cleanup_Refactor.
5. THE Silco SHALL keep `discover` importable from `silco.plugins` after the Cleanup_Refactor.
6. THE Silco SHALL keep `load_ipython_extension`, `unload_ipython_extension`, and `install` importable from `silco.plugins.ipython` after the Cleanup_Refactor.
7. THE Silco SHALL keep `pdf_renderer` and `save_pdf` importable from `silco.plugins.pdf` after the Cleanup_Refactor.
8. WHERE the pre-refactor codebase exposes a deeper module path that user code may import (for example `silco.core.renderers.base.diagram.Diagram` or `silco.core.renderers.svg_common.render_mermaid`), THE Silco SHALL keep that import path resolvable after the Cleanup_Refactor.

### Requirement 2: Preserve method signatures and chaining aliases

**User Story:** As a Silco user, I want every documented method on `Diagram` to keep the same name, signature, and chainable alias, so that fluent diagram code keeps working.

#### Acceptance Criteria

1. THE Diagram SHALL expose `add_node` and its alias `node` with the same parameter list and defaults as before the Cleanup_Refactor.
2. THE Diagram SHALL expose `add_group` and its alias `group` with the same parameter list and defaults as before the Cleanup_Refactor.
3. THE Diagram SHALL expose `add_edge` and its alias `connect` with the same parameter list and defaults as before the Cleanup_Refactor.
4. THE Diagram SHALL expose `add_flow` and its alias `flow` with the same parameter list and defaults as before the Cleanup_Refactor.
5. THE Diagram SHALL expose `render`, `layout`, `to_svg`, `to_mermaid`, `to_html`, `to_pdf`, `save_pdf`, `_repr_svg_`, and `_repr_html_` with the same parameter list and defaults as before the Cleanup_Refactor.
6. WHEN any chainable method is called, THE Diagram SHALL return the same `Diagram` instance to support fluent chaining.
7. THE Diagram SHALL keep the same Pydantic field names, defaults, and validators on `title`, `direction`, `nodes`, `edges`, `flows`, `groups`, and `metadata` after the Cleanup_Refactor.

### Requirement 3: Preserve renderer output equivalence

**User Story:** As a Silco user, I want diagrams I render before and after the refactor to produce equivalent output, so that downstream files, snapshots, and notebooks do not change.

#### Acceptance Criteria

1. FOR ANY Diagram constructed using only Public_API calls, THE Silco SHALL produce a Mermaid_Output that is byte-identical to the pre-refactor Mermaid_Output for the same Diagram.
2. FOR ANY Diagram constructed using only Public_API calls, and for each style in `kernel.names("styles")` and each layout in `kernel.names("layouts")`, THE Silco SHALL produce an SVG_Output that is Behavior_Equivalent to the pre-refactor SVG_Output for the same Diagram and the same options.
3. WHEN `Diagram.to_html(**options)` is called, THE Silco SHALL return a string that contains the SVG_Output produced by `Diagram.to_svg(**options)` wrapped in the same `<div class="silco-diagram">...</div>` envelope as before the Cleanup_Refactor.
4. WHEN `Diagram.to_pdf()` is called and the optional CairoSVG dependency is available, THE Silco SHALL return PDF bytes derived from the same SVG_Output as before the Cleanup_Refactor.
5. IF the optional CairoSVG dependency is missing, THEN THE Silco SHALL raise a `RuntimeError` whose message instructs the user to install the `silco[pdf]` extra, matching the pre-refactor message intent.
6. WHEN `Diagram.save_pdf(path)` is called, THE Silco SHALL write a PDF file to `path` and return a `pathlib.Path` pointing to that file.

### Requirement 4: Preserve plugin registration and discovery

**User Story:** As a Silco integrator, I want the kernel to expose the same plugin categories and names after the refactor, so that plugin lookups and entry-point discovery keep working.

#### Acceptance Criteria

1. THE Plugin_Registry SHALL report the same set of categories from `kernel.categories()` after the Cleanup_Refactor as before, namely `("shapes", "renderers", "layouts", "presenters", "styles")`.
2. WHEN `silco` is imported, THE Plugin_Registry SHALL register the Built_in_Plugins `dag` and `grid` under category `layouts`, `svg` and `mermaid` under category `renderers`, and `modern` and `uml` under category `styles`.
3. THE Plugin_Registry SHALL register each Built_in_Plugin name exactly once after `silco` is imported.
4. WHEN `silco.plugins.ipython` is imported, THE Plugin_Registry SHALL register a presenter named `ipython`.
5. WHEN `silco.plugins.pdf` is imported, THE Plugin_Registry SHALL register a renderer named `pdf`.
6. WHEN `kernel.discover()` is called with default arguments, THE Plugin_Registry SHALL return only plugins registered as a result of that call and SHALL NOT raise on repeat invocation.
7. THE Plugin_Registry SHALL keep `kernel.register`, `kernel.get`, `kernel.info`, `kernel.list`, `kernel.names`, `kernel.categories`, `kernel.normalize_category`, `kernel.discover`, `kernel.discover_namespace`, and `kernel.discover_entry_points` callable with the same parameter list and defaults as before the Cleanup_Refactor.

### Requirement 5: Preserve CLI and notebook integration

**User Story:** As a Silco user running the demo or a notebook, I want the CLI and IPython hooks to keep working without changes to my workflow, so that I do not have to relearn how to use the tool.

#### Acceptance Criteria

1. WHEN `python main.py` is run with the `silco[pdf]` extra installed and Graphviz available, THE CLI_Entry SHALL produce a PDF file at the path `checkout-demo.pdf` relative to the working directory.
2. IF `python main.py` is run without the `silco[pdf]` extra, THEN THE CLI_Entry SHALL exit with a `SystemExit` whose message instructs the user to install the PDF extras.
3. WHEN a user evaluates `%load_ext silco.plugins.ipython` in an IPython shell, THE Silco SHALL register `image/svg+xml` and `text/html` formatters for the `Diagram` type.
4. WHEN a user evaluates `%unload_ext silco.plugins.ipython` in an IPython shell, THE Silco SHALL remove the formatters for the `Diagram` type from `image/svg+xml` and `text/html`.
5. THE Tutorial_Notebook SHALL execute end to end after the Cleanup_Refactor without modification, producing the same set of cell outputs to within Behavior_Equivalent SVG and identical Mermaid text.

### Requirement 6: Remove unreachable and dead code

**User Story:** As a Silco maintainer, I want unreachable code paths and unused helpers removed, so that the codebase is smaller and easier to read.

#### Acceptance Criteria

1. THE Silco SHALL NOT contain any module-level function, class, or constant that is not reachable from the Public_API, the CLI_Entry, the Plugin_Registry registration code, or test code, after the Cleanup_Refactor.
2. THE Silco SHALL remove the unused helpers `render_group_bounds`, `group_path`, `curved_edge`, `stereotype_text`, `centered_label`, `actor_text`, and `template_shape` from `silco/core/renderers/svg_common.py` if no consumer is found.
3. THE Silco SHALL remove the unused private helpers `_svg_node`, `_svg_edge`, `_svg_node_shape`, `_svg_actor`, `_svg_component`, `_svg_database`, `_svg_queue`, `_svg_cache`, `_svg_storage`, and `_svg_external` from `silco/core/renderers/exporter/svg.py` if no consumer is found.
4. WHERE a removed helper has any remaining caller, THE Cleanup_Refactor SHALL keep the helper or relocate it before removing the original definition.
5. THE Silco SHALL remove the empty `silco/core/utils/` package if it remains empty after the Cleanup_Refactor.
6. THE Silco SHALL remove unused template asset files under `silco/core/templates/shapes/` if no remaining code path references them, except for files referenced by the `actor` shape pipeline.
7. IF the Cleanup_Refactor cannot statically prove a module-level symbol is dead, THEN THE Cleanup_Refactor SHALL leave the symbol in place and document the uncertainty.

### Requirement 7: Eliminate duplicate plugin registrations

**User Story:** As a Silco maintainer, I want each plugin to be registered exactly once, so that registration order and source of truth are unambiguous.

#### Acceptance Criteria

1. WHEN `silco` is imported, THE Plugin_Registry SHALL register the `mermaid` renderer exactly once.
2. WHEN `silco` is imported, THE Plugin_Registry SHALL register each of the `svg`, `dag`, `grid`, `modern`, and `uml` Built_in_Plugins exactly once.
3. THE Cleanup_Refactor SHALL designate a single canonical registration site per Built_in_Plugin and remove other registration paths for that plugin.
4. THE Cleanup_Refactor SHALL preserve the description and tags currently associated with each Built_in_Plugin name as returned by `kernel.info(category, name)`.

### Requirement 8: Standardize module-level conventions

**User Story:** As a Silco maintainer, I want consistent module headers and type hint conventions, so that reading any file in the project feels predictable.

#### Acceptance Criteria

1. THE Silco SHALL include `from __future__ import annotations` at the top of every Python module under `silco/` after the Cleanup_Refactor.
2. THE Silco SHALL keep the public type aliases `NodeKind`, `Direction`, `PluginCategory`, and `PluginType` resolvable from their current import paths after the Cleanup_Refactor.
3. THE Silco SHALL keep every public class and public top-level function under `silco/` carrying a one-line docstring after the Cleanup_Refactor.
4. WHERE the pre-refactor code uses `dict`, `list`, `tuple`, `set`, or `type` as generic annotations, THE Silco SHALL continue to use the built-in generic syntax instead of importing from `typing` after the Cleanup_Refactor.
5. WHERE the pre-refactor code references unused imports, THE Silco SHALL remove those imports after the Cleanup_Refactor.

### Requirement 9: Tighten and align package re-exports

**User Story:** As a Silco user, I want `silco`, `silco.core`, and `silco.core.models` to declare a clear and consistent set of re-exports, so that I can rely on `__all__` and IDE autocomplete.

#### Acceptance Criteria

1. THE Silco SHALL declare a non-empty `__all__` in `silco/__init__.py`, `silco/core/__init__.py`, `silco/core/models/__init__.py`, `silco/plugins/__init__.py`, and `silco/plugins/renderers/__init__.py` after the Cleanup_Refactor.
2. THE Silco SHALL include every name listed in Requirement 1 acceptance criteria 1 in the `__all__` of `silco/__init__.py`.
3. THE Silco SHALL include every name listed in Requirement 1 acceptance criterion 3 in the `__all__` of `silco/core/__init__.py`.
4. THE Silco SHALL keep `__all__` entries sorted in a single, consistent order (alphabetical by lowercase) across the listed packages after the Cleanup_Refactor.
5. WHERE a sub-module is imported only for its side effects (plugin registration), THE Silco SHALL document the side-effect import with a comment after the Cleanup_Refactor.

### Requirement 10: Deduplicate helpers and simplify renderer structure

**User Story:** As a Silco maintainer, I want overlapping renderer plumbing collapsed into a single, clear structure, so that adding new renderers or styles is straightforward.

#### Acceptance Criteria

1. THE Silco SHALL keep `DiagramStyle` importable from `silco.core.renderers.diagrams_backend` after the Cleanup_Refactor.
2. WHERE the pre-refactor code provides re-export shims (for example `silco/core/renderers/style.py`), THE Cleanup_Refactor SHALL keep those import paths resolvable.
3. THE Silco SHALL collapse the `Edge`/`Flow` relation-append helper on `Diagram` into a single internal method that handles both relation types after the Cleanup_Refactor.
4. THE Silco SHALL keep the runtime semantics of `dag_layout`, `grid_layout`, and the SVG rendering pipeline identical to the pre-refactor implementation, as measured by Renderer_Output equivalence on representative diagrams.

### Requirement 11: Preserve packaging metadata and entry points

**User Story:** As a Silco packager, I want `pyproject.toml` and the entry points to keep advertising the same plugins and package data, so that wheels and installs continue to work.

#### Acceptance Criteria

1. THE Silco SHALL keep the `[project.entry-points."silco.plugins"]` table in `pyproject.toml` advertising `ipython = "silco.plugins.ipython"` and `pdf = "silco.plugins.pdf"` after the Cleanup_Refactor.
2. THE Silco SHALL keep the `[tool.setuptools.package-data]` entries that include shape templates installed in built wheels for any template files that remain in the source tree after Requirement 6.
3. THE Silco SHALL keep the `[project.optional-dependencies]` groups `notebook` and `pdf` advertising the same dependencies as before the Cleanup_Refactor.
4. THE Silco SHALL keep the `requires-python` floor and runtime dependency list in `pyproject.toml` unchanged unless a removal under Requirement 6 makes a dependency unused, in which case THE Silco SHALL keep it listed if it remains a transitive runtime requirement of any non-removed module.

### Requirement 12: Verifiable behavior parity

**User Story:** As a Silco maintainer, I want an automated way to confirm the refactor preserves behavior, so that I can review the change with confidence.

#### Acceptance Criteria

1. THE Cleanup_Refactor SHALL include a snapshot or property-style check that, for a fixed set of representative diagrams, asserts the Mermaid_Output is byte-identical before and after the refactor.
2. THE Cleanup_Refactor SHALL include a snapshot or property-style check that, for a fixed set of representative diagrams across each registered style, asserts the SVG_Output is Behavior_Equivalent before and after the refactor.
3. THE Cleanup_Refactor SHALL include an import-surface check that imports every name listed in Requirement 1 acceptance criteria 1, 3, 4, 5, 6, and 7 and asserts the import succeeds.
4. THE Cleanup_Refactor SHALL include a registry check that asserts `kernel.names(category)` for each category returns a set equal to the pre-refactor set for that category.
5. WHEN any check in this requirement fails, THE Cleanup_Refactor SHALL be considered incomplete and SHALL NOT be merged.

### Requirement 13: Error and validation behavior preservation

**User Story:** As a Silco user, I want input validation and error messages to behave the same after the refactor, so that my error-handling code keeps working.

#### Acceptance Criteria

1. WHEN `Diagram.add_node` is called with an `id` that already exists, THE Diagram SHALL raise `ValueError` with a message containing the duplicate id, matching the pre-refactor message intent.
2. WHEN `Diagram.add_edge` or `Diagram.add_flow` is called with an unknown source or target, THE Diagram SHALL raise `ValueError` whose message identifies the unknown endpoint.
3. WHEN a `Diagram` is constructed with `direction` outside `{"LR", "RL", "TB", "BT"}`, THE Diagram SHALL raise a Pydantic validation error.
4. WHEN `kernel.normalize_category` is called with a value outside the documented aliases, THE Plugin_Registry SHALL raise `ValueError` listing the valid categories.
5. WHEN `Diagram.to_svg` is called and the `diagrams` package is missing, THE Silco SHALL raise `RuntimeError` whose message instructs the user to install project dependencies.
