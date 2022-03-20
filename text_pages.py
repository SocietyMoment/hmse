from flask import Blueprint, render_template
from auth import login_required

text_bp = Blueprint('text_pages', __name__)

@text_bp.route("/todo")
@login_required(fail=False)
def todo_page(user):
    return render_template("todo.html", user=user)
