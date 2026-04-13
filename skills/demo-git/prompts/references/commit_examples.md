# Demo Repo Commit Examples

Use short commit messages.
Keep one turn's work in one commit when you can.

Examples:

```bash
git -C repos/demo_repo add .
git -C repos/demo_repo commit -m "feat: add calculator skeleton"
```

```bash
git -C repos/demo_repo add docs/README.md tests/test_readme.py
git -C repos/demo_repo commit -m "docs: explain calculator usage"
```

```bash
git -C repos/demo_repo add src/app.py tests/test_app.py
git -C repos/demo_repo commit -m "fix: return stable greeting"
```
