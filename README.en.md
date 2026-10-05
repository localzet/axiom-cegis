# axiom-cegis v0.2.0

A concrete CEGIS loop. The synthesizer starts with examples, proposes the cheapest program consistent with them, and
asks `axiom-symbolic` for either a universal proof or a counterexample. Counterexamples become new examples until the
loop converges.

For the bundled `abs` experiment the intended trajectory is:

```text
x        -> counterexample x < 0
-x       -> counterexample x > 0
branch   -> VALID for all integers
```

## Авторство

Сопровождающий собственных изменений: **Ivan Zorin (localzet)** — <creator@localzet.com> · https://www.localzet.com. Copyright © 2026 Localzet Group. Исходное авторство и лицензии сторонних компонентов сохраняются. См. [AUTHORS](.github/AUTHORS.md).
