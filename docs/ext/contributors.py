from docutils.parsers.rst import Directive
from docutils.nodes import paragraph


class ContributorsDirective(Directive):

    required_arguments = 1
    has_content = True

    def run(self):
        role = self.arguments[0]

        roles = ["authors", "translators", "artists"]
        if role not in roles:
            raise Exception("Argument must be in {}".format(roles))

        const = self.state.document.settings.env.config.const
        if role == "authors":
            people = const.AUTHORS
        elif role == "translators":
            people = const.TRANSLATORS
        else:
            people = const.ARTISTS

        output = ", ".join(people)
        return [paragraph(text=output)]


def setup(app):
    app.add_directive("contributors", ContributorsDirective)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
