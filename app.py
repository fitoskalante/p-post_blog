from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, current_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Blog secret key'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'signin'

app.secret_key = 'My secret key'


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(30), nullable=False, unique=True)
    password = db.Column(db.String(30), nullable=False)
    posts = db.relationship('Post', backref='user', lazy=True)
    # a list of post that this user likes
    like_post = db.relationship(
        'Post', secondary='likes', backref='my_likes', lazy=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), server_onupdate=db.func.now())
    view_count = db.Column(db.Integer, default=0)


likes = db.Table('likes',
                 db.Column('user_id', db.Integer, db.ForeignKey(
                     'users.id'), primary_key=True),
                 db.Column('post_id', db.Integer, db.ForeignKey('posts.id'), primary_key=True))


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    post_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), server_onupdate=db.func.now())


db.create_all()


@login_manager.user_loader
def load_user(id):
    return User.query.get(id)


@app.route('/like/board/<int:id>', methods=['post'])
@login_required
def like_post_on_board(id):
    post = Post.query.get(id)
    print(request.url)
    if not post:
        flash('go away')
        return redirect(url_for('root'))
    if not current_user.like_post:
        current_user.like_post.append(post)
        db.session.commit()
        if request.url == "http://localhost:5000/like/board/<id>":
            return redirect(url_for('root'))
        return redirect(url_for('render_post', id=id))
    if current_user.like_post:
        current_user.like_post.remove(post)
        db.session.commit()
        if request.url == "http://localhost:5000/like/board/<id>":
            return redirect(url_for('root'))
        return redirect(url_for('render_post', id=id))
    return redirect(url_for('root'))


# @app.route('/like/post/<int:id>', methods=['post'])
# @login_required
# def like_post(id):
#     post = Post.query.get(id)
#     print(current_user.like_post)
#     if not post:
#         flash('go away')
#         return redirect(url_for('render_post', id=id))
#     if not current_user.like_post:
#         current_user.like_post.append(post)
#         db.session.commit()
#         return redirect(url_for('render_post', id=id))
#     if current_user.like_post:
#         current_user.like_post.remove(post)
#         db.session.commit()
#         return redirect(url_for('render_post', id=id))
#     return redirect(url_for('render_post', id=id))


@app.route('/', methods=['GET', 'POST'])
@login_required
def root():
    posts = Post.query.all()
    if request.method == 'POST':
        new_post = Post(title=request.form['title'],
                        body=request.form['body'],
                        user_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('root'))
    return render_template('views/index.html', posts=posts)


@app.route('/post/<id>/comments', methods=['GET', 'POST'])
@login_required
def leave_comment(id):
    print('first')
    comments = Comment.query.filter_by(post_id=id).all()
    if request.method == 'POST':
        new_comment = Comment(body=request.form['body'],
                              user_id=current_user.id,
                              post_id=id)
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('render_post', id=id, comments=comments))
    return redirect(url_for('render_post', id=id, comments=comments))


@app.route('/post/<id>/delete', methods=['GET', 'POST'])
@login_required
def delete_post(id):
    if request.method == 'POST':
        post = Post.query.filter_by(id=id).first()
        if not post:
            flash('No shuch a post', 'warning')
            return redirect(url_for('root'))
        db.session.delete(post)
        db.session.commit()
        return redirect(url_for('root'))
    return redirect(url_for('root'))


@app.route('/post/<id>', methods=['GET', 'POST'])
@login_required
def render_post(id):
    comments = Comment.query.filter_by(post_id=id).all()
    post = Post.query.get(id)
    post.view_count += 1
    db.session.add(post)
    db.session.commit()
    if not post:
        return redirect(url_for('root'))
    if request.method == 'POST':
        post.title = request.form['title']
        post.body = request.form['body']
        db.session.commit()
        return redirect(url_for('render_post', id=id))
    return render_template('views/post.html', current_post=post, comments=comments)


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if not user:
            flash('Email not registered, please try again.', 'warning')
            return redirect(url_for('signin'))
        if user.check_password(password=request.form['password']):
            login_user(user)
            flash('Welcome back {}'.format(
                current_user.username) + '!', 'success')
            return redirect(url_for('root'))
        flash('Wrong password, please try again', 'warning')
        return redirect(url_for('signin'))
    if current_user.is_authenticated:
        return redirect(url_for('root'))
    return render_template('views/sign-in-form.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        check_email = User.query.filter_by(email=request.form['email']).first()
        if check_email:
            flash('Email already registered', 'warning')
            return redirect(url_for('signup'))
        new_user = User(email=request.form['email'],
                        username=request.form['username'])
        new_user.set_password(request.form['password'])

        db.session.add(new_user)
        db.session.commit()
        flash('Welcome, you have successfully signed up!', 'success')
        return redirect(url_for('root'))
    if current_user.is_authenticated:
        return redirect(url_for('root'))
    return render_template('views/sign-up-form.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('signin'))


if __name__ == "__main__":
    app.run(debug=True)
