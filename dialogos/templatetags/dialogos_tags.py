from django import template

from django.contrib.contenttypes.models import ContentType

from dialogos.forms import UnauthenticatedCommentForm, AuthenticatedCommentForm
from dialogos.models import Comment


register = template.Library()


class BaseCommentNode(template.Node):
    @classmethod
    def handle_token(cls, parser, token):
        bits = token.split_contents()
        if not cls.requires_as_var and len(bits) == 2:
            return cls(parser.compile_filter(bits[1]))
        elif len(bits) == 4:
            if bits[2] != "as":
                raise template.TemplateSyntaxError("%r's 2nd argument must be 'as'" % bits[0])
            return cls(parser.compile_filter(bits[1]), bits[3])
        if cls.requires_as_var:
            args = "1 argument"
        else:
            args = "either 1 or 3 arguments"
        raise template.TemplateSyntaxError("%r takes %s" % (bits[0], args))

    def __init__(self, obj, varname=None):
        self.obj = obj
        self.varname = varname
    
    def get_comments(self, context):
        obj = self.obj.resolve(context)
        return Comment.objects.filter(
            object_id=obj.pk,
            content_type=ContentType.objects.get_for_model(obj)
        )

class CommentCountNode(BaseCommentNode):
    requires_as_var = False
    
    def render(self, context):
        comments = self.get_comments(context).count()
        if self.varname is not None:
            context[self.varname] = comments
            return ""
        return unicode(comments)


class CommentsNode(BaseCommentNode):
    requires_as_var = True
    
    def render(self, context):
        context[self.varname] = self.get_comments(context)
        return ""


class CommentFormNode(BaseCommentNode):
    requires_as_var = False
    
    def render(self, context):
        obj = self.obj.resolve(context)
        user = context.get("user")
        if user is None or not user.is_authenticated():
            form = UnauthenticatedCommentForm(obj=obj)
        else:
            form = AuthenticatedCommentForm(obj=obj)
        context[self.varname] = form
        return ""


@register.tag
def comment_count(parser, token):
    """
    Usage:
        
        {% comment_count obj %}
    or
        {% comment_count obj as var %}
    """
    return CommentCountNode.handle_token(parser, token)

@register.tag
def comments(parser, token):
    """
    Usage:
        
        {% comments obj as var %}
    """
    return CommentsNode.handle_token(parser, token)

@register.tag
def comment_form(parser, token):
    """
    Usage:
        
        {% comment_form obj as comment_form %}
        
    Will read the `user` var out of the contex to know if the form should be
    form an auth'd user or not.
    """
    return CommentFormNode.handle_token(parser, token)
