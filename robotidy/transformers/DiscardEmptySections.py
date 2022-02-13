from robot.api.parsing import ModelTransformer, EmptyLine, Comment, CommentSection
from robotidy.decorators import check_start_end_line
from robotidy.generate_config import TransformerGenConfig, Parameter, ValidateInt, ParameterBool


class DiscardEmptySections(ModelTransformer):
    """
    Remove empty sections.
    Sections are considered empty if there are only empty lines inside.
    You can remove sections with only comments by setting ``allow_only_comments`` parameter to False:

        *** Variables ***
        # this section will be removed with``allow_only_comments`` parameter set to False

    Supports global formatting params: ``--startline`` and ``--endline``.

    See https://robotidy.readthedocs.io/en/latest/transformers/DiscardEmptySections.html for more examples.
    """

    def __init__(self, allow_only_comments: bool = True):
        # If False then sections with only with comments are considered to be empty
        self.allow_only_comments = allow_only_comments

    def generate_config(self):
        config = TransformerGenConfig(
            name=self.__class__.__name__,
            enabled=self.__dict__.get("ENABLED", True),
            msg="Do you want to remove empty sections?",
        )
        if not config.enabled:
            return config
        allow_only_comments = ParameterBool(
            "Sections are considered empty if there are only empty lines inside. You can optionally also remove "
            "sections that contains only comments (except `*** Comments ***` section):",
            "allow_only_comments",
            self.allow_only_comments,
            "Allow sections only with comments",
            "Remove sections only with comments",
        )
        config.parameters.append(allow_only_comments)
        return config

    @check_start_end_line
    def visit_Section(self, node):  # noqa
        anything_but = (
            EmptyLine if self.allow_only_comments or isinstance(node, CommentSection) else (Comment, EmptyLine)
        )
        if all(isinstance(child, anything_but) for child in node.body):
            return None
        return node
