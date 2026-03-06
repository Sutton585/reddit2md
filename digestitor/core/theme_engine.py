
import os
from string import Template

class ThemeEngine:
    """
    Standard library templating engine for Sandman Project modules.
    Swaps ${variable} placeholders in .template files for real data.
    """
    def __init__(self, template_dir):
        self.template_dir = template_dir
        self._cache = {}

    def _load_template(self, name):
        if name not in self._cache:
            path = os.path.join(self.template_dir, f"{name}.template")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self._cache[name] = Template(f.read())
            except FileNotFoundError:
                print(f"Warning: Template {name} not found at {path}")
                self._cache[name] = Template(f"Missing Template: {name}\n${{content}}")
        return self._cache[name]

    def render(self, template_name, **kwargs):
        """Renders a named template with the provided variables."""
        tmpl = self._load_template(template_name)
        # safe_substitute prevents crashes if a variable is missing
        return tmpl.safe_substitute(**kwargs)
