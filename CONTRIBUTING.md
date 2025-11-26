# Contributing to aare.ai

Thank you for your interest in contributing to aare.ai! We welcome contributions from the community and are grateful for any help you can provide.

## 🤝 Code of Conduct

Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

## 🚀 Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/aare-aws.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Run tests: `pytest tests/`
6. Commit: `git commit -am 'Add new feature'`
7. Push: `git push origin feature/your-feature-name`
8. Create a Pull Request

## 📝 Pull Request Process

1. Update the README.md with details of changes to the interface
2. Add tests for any new functionality
3. Ensure all tests pass
4. Update documentation as needed
5. Request review from maintainers

## 🧩 Contributing Ontologies

We especially welcome ontology contributions! To contribute an ontology:

1. Create your ontology in OWL format
2. Place it in `ontologies/community/`
3. Add documentation in `ontologies/community/README.md`
4. Include test cases in `tests/ontologies/`
5. Submit a PR with a clear description of the domain and constraints

### Ontology Guidelines

- Use clear, descriptive names for classes and properties
- Include comprehensive documentation
- Provide example inputs that should pass/fail verification
- Follow OWL 2 DL profile for decidability
- Include metadata (author, version, license)

## 🐛 Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- A clear, descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- System information (OS, Python version, etc.)
- Relevant logs or error messages

## 💡 Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- A clear, descriptive title
- Detailed description of the proposed functionality
- Use cases and examples
- Potential implementation approach (if known)
- Any relevant mockups or diagrams

## 🔧 Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/ -v

# Run linting
black src/ tests/
pylint src/
mypy src/
```

## 📚 Documentation

- Code should be self-documenting with clear variable/function names
- Add docstrings to all functions and classes
- Update relevant documentation for any changed functionality
- Include inline comments for complex logic

## 🧪 Testing

- Write unit tests for all new functionality
- Maintain or improve code coverage (aim for >80%)
- Include integration tests for Lambda handlers
- Test edge cases and error conditions

## 📋 Commit Guidelines

We follow conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Test additions or changes
- `chore:` Maintenance tasks

Example: `feat: add support for temporal constraints in SMT verifier`

## 🏆 Recognition

Contributors will be recognized in:

- The project README
- Release notes
- Our website's contributors page

## 📬 Contact

- Discord: [Join our community](https://discord.gg/aare-ai)
- Email: contribute@aare.ai
- GitHub Discussions: [Ask questions](https://github.com/aare-ai/aare-aws/discussions)

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for helping make aare.ai better! 🎉