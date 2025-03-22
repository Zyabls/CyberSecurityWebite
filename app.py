from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
import time
from werkzeug.utils import secure_filename
import matplotlib.pyplot as plt
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cybersecurity_courses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuration for file uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Models
class ModuleProgress(db.Model):
    __tablename__ = 'module_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)

class Enrollment(db.Model):
    __tablename__ = 'enrollment'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    progress = db.Column(db.Float, default=0.0)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed = db.Column(db.DateTime)
    start_time = db.Column(db.DateTime)  # New field for start time
    end_time = db.Column(db.DateTime)    # New field for end time

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_instructor = db.Column(db.Boolean, default=False)
    courses_created = db.relationship('Course', backref='author', lazy=True)
    enrolled_courses = db.relationship('Course',
                                   secondary='enrollment',
                                   backref=db.backref('enrolled_users', lazy='dynamic'),
                                   primaryjoin="User.id == Enrollment.user_id",
                                   secondaryjoin="Enrollment.course_id == Course.id",
                                   lazy='dynamic')
    test_results = db.relationship('TestResult', backref='user', lazy=True)
    module_progress = db.relationship('ModuleProgress', backref='user', lazy=True)

class Course(db.Model):
    __tablename__ = 'course'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    modules = db.relationship('Module', backref='course', lazy='dynamic')
    image_path = db.Column(db.String(200))

    def get_progress(self, user_id):
        total_modules = self.modules.count()
        if total_modules == 0:
            return 0
        
        completed_modules = ModuleProgress.query.join(Module).filter(
            Module.course_id == self.id,
            ModuleProgress.user_id == user_id,
            ModuleProgress.completed == True
        ).count()
        
        return (completed_modules / total_modules) * 100

class Module(db.Model):
    __tablename__ = 'module'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=True)
    order = db.Column(db.Integer)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    tests = db.relationship('Test', backref='module', lazy=True)
    progress = db.relationship('ModuleProgress', backref='module', lazy=True)

    def is_completed(self, user_id):
        module_tests = Test.query.filter_by(module_id=self.id).all()
        if not module_tests:
            progress = ModuleProgress.query.filter_by(module_id=self.id, user_id=user_id).first()
            return progress is not None
        
        for test in module_tests:
            result = test.get_user_result(user_id)
            if not result or result.score < 70:
                return False
        
        return True

class Test(db.Model):
    __tablename__ = 'test'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    questions = db.relationship('Question', backref='test', lazy=True)
    results = db.relationship('TestResult', backref='test', lazy=True)

    def get_user_result(self, user_id):
        return TestResult.query.filter_by(test_id=self.id, user_id=user_id).order_by(TestResult.completed_at.desc()).first()

class TestResult(db.Model):
    __tablename__ = 'test_result'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

class Question(db.Model):
    __tablename__ = 'question'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(100), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)

def init_db():
    """Инициализация базы данных."""
    print("Инициализация базы данных...")
    try:
        db.drop_all()
        print("Все таблицы удалены.")
        
        db.create_all()
        print("Все таблицы созданы.")
        
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                password=generate_password_hash('admin', method='sha256'),
                is_instructor=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Создан администратор.")
        
        print("Инициализация базы данных завершена.")
    except Exception as e:
        print(f"Ошибка инициализации базы данных: {str(e)}")
        raise

@app.route('/report_selection', methods=['GET', 'POST'])
@login_required
def report_selection():
    courses = Course.query.all()
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        return redirect(url_for('generate_user_report', course_id=course_id))

    return render_template('report_selection.html', courses=courses)

@app.route('/report/users/<int:course_id>')
def generate_user_report(course_id):
    course = Course.query.get(course_id)
    if not course:
        return "Курс не найден", 404

    # Получаем всех студентов, зарегистрированных на курс
    students = User.query.join(Enrollment).filter(Enrollment.course_id == course_id).all()

    # Сбор данных для отчета
    report_data = []
    for student in students:
        # Получаем результаты тестов для каждого студента
        test_results = TestResult.query.filter_by(user_id=student.id).all()
        
        # Подсчет среднего балла
        total_tests = len(test_results)
        average_score = (sum(result.score for result in test_results) / total_tests) if total_tests > 0 else 0
        
        # Получаем информацию о посещениях
        enrollment = Enrollment.query.filter_by(user_id=student.id, course_id=course_id).first()

        # Calculate completion time
        if enrollment and enrollment.end_time:
            total_seconds = (enrollment.end_time - enrollment.start_time).total_seconds()
            completion_time = total_seconds  # Keep it in seconds for graphing
        else:
            completion_time = float('inf')  # Use infinity for not completed courses

        report_data.append({
            'username': student.username,
            'average_score': average_score,
            'total_tests': total_tests,
            'enrollment_date': enrollment.enrolled_at,
            'last_accessed': enrollment.last_accessed,
            'completion_time': int(completion_time)  # Keep in seconds for graphing
        })

    # Создание линейного графика для скорости прохождения курса
    plt.figure(figsize=(10, 5))
    plt.plot([data['username'] for data in report_data], [-data['completion_time'] for data in report_data], marker='o', color='green')  # Invert the time
    plt.xlabel('Студенты')
    plt.ylabel('Скорость прохождения курса (отрицательное время в секундах)')
    plt.title('Скорость прохождения курса')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Сохранение графика в статическую директорию
    speed_graph_path = os.path.join('static', 'images', 'user_report_speed.png')
    plt.savefig(speed_graph_path)
    plt.close()

    # Создание графика для среднего балла
    plt.figure(figsize=(10, 5))
    plt.bar([data['username'] for data in report_data], [data['average_score'] for data in report_data], color='blue')
    plt.xlabel('Студенты')
    plt.ylabel('Средний балл')
    plt.title('Средний балл студентов по курсу {}'.format(course.title))
    plt.xticks(rotation=45)
    plt.tight_layout()

    score_graph_path = os.path.join('static', 'images', 'user_report_score.png')
    plt.savefig(score_graph_path)
    plt.close()

    # Отправляем данные в шаблон для отображения
    return render_template('user_report.html', course=course, report_data=report_data, speed_graph_path=speed_graph_path, score_graph_path=score_graph_path)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_instructor = request.form.get('is_instructor') == 'on'

        user = User.query.filter_by(username=username).first()
        if user:
            flash('Имя пользователя уже существует')  # Переведено
            return redirect(url_for('register'))

        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password, method='sha256'),
            is_instructor=is_instructor
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            flash('Пожалуйста, проверьте свои данные для входа и попробуйте снова.')  # Переведено
            return redirect(url_for('login'))

        login_user(user, remember=remember)
        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    courses = Course.query.all()
    return render_template('index.html', courses=courses)

@app.route('/create_course', methods=['GET', 'POST'])
@login_required
def create_course():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        # Handle image upload
        image = request.files.get('image')
        image_path = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            filename = f"{int(time.time())}_{filename}"
            image_path = os.path.join('uploads', filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        try:
            # Create course
            course = Course(
                title=title,
                description=description,
                image_path=image_path,
                author_id=current_user.id
            )
            db.session.add(course)
            db.session.commit()
            
            # Get module data
            module_titles = request.form.getlist('module_title[]')
            module_descriptions = request.form.getlist('module_description[]')
            
            # Create modules
            for i, (title, description) in enumerate(zip(module_titles, module_descriptions)):
                if title.strip():
                    module = Module(
                        title=title,
                        content=description,
                        course_id=course.id,
                        order=i
                    )
                    db.session.add(module)
                    db.session.commit()
                    
                    # Get test data
                    test_title = request.form.get(f'test_title_{i+1}')
                    if test_title and test_title.strip():
                        test = Test(
                            title=test_title,
                            module_id=module.id
                        )
                        db.session.add(test)
                        db.session.commit()
                        
                        # Get questions data
                        question_texts = request.form.getlist(f'question_text_{i+1}[]')
                        correct_answers = request.form.getlist(f'correct_answer_{i+1}[]')
                        
                        # Create questions and options
                        for j, (q_text, c_answer) in enumerate(zip(question_texts, correct_answers)):
                            if q_text.strip() and c_answer.strip():
                                # Get options for this question
                                options = request.form.getlist(f'options_{i+1}_{j+1}[]')
                                options = [opt.strip() for opt in options if opt.strip()]
                                
                                if options:  # Only create question if it has options
                                    question = Question(
                                        content=q_text,
                                        correct_answer=c_answer,
                                        options='\n'.join(options),
                                        test_id=test.id
                                    )
                                    db.session.add(question)
            
            db.session.commit()
            return redirect(url_for('view_course', course_id=course.id))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating course: {str(e)}")
            return render_template('create_course.html')
    
    return render_template('create_course.html')

@app.route('/create_test/<int:module_id>', methods=['GET', 'POST'])
@login_required
def create_test(module_id):
    module = Module.query.get_or_404(module_id)
    course = Course.query.get(module.course_id)
    
    if current_user.id != course.author_id:
        return redirect(url_for('view_course', course_id=course.id))

    if request.method == 'POST':
        title = request.form.get('title')
        if not title:
            return render_template('create_test.html', module_id=module_id)
            
        # Create test
        test = Test(
            title=title,
            module_id=module_id
        )
        db.session.add(test)
        
        try:
            db.session.commit()  # Save test to get its ID
            
            # Get questions data
            questions = request.form.getlist('questions[]')
            correct_answers = request.form.getlist('correct_answers[]')
            
            # Create questions
            for i, (question_text, correct_answer) in enumerate(zip(questions, correct_answers)):
                if question_text and correct_answer:
                    # Get options for current question
                    options = request.form.getlist(f'options_{i+1}[]')
                    if options:
                        # Create question
                        question = Question(
                            content=question_text.strip(),
                            correct_answer=correct_answer.strip(),
                            options='\n'.join(opt.strip() for opt in options if opt.strip()),
                            test_id=test.id
                        )
                        db.session.add(question)
            
            db.session.commit()
            return redirect(url_for('view_module', module_id=module_id))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating test: {str(e)}")  # For debugging
            return render_template('create_test.html', module_id=module_id)

    return render_template('create_test.html', module_id=module_id)

@app.route('/course/<int:course_id>') 
@login_required
def view_course(course_id):
    course = Course.query.get_or_404(course_id)
    is_enrolled = course.enrolled_users.filter_by(id=current_user.id).first() is not None
    is_author = course.author_id == current_user.id
    
    # Get enrollment for progress
    enrollment = None
    if is_enrolled:
        enrollment = Enrollment.query.filter_by(
            user_id=current_user.id,
            course_id=course_id
        ).first()
    
    # Calculate course progress
    course_progress = 0
    if enrollment:
        course_progress = course.get_progress(current_user.id)
        # Update enrollment progress
        enrollment.progress = course_progress
        db.session.commit()
    
    # Get modules with completion status
    modules = []
    for module in course.modules.order_by(Module.order):
        module_data = {
            'module': module,
            'is_completed': module.is_completed(current_user.id) if is_enrolled else False,
            'test_results': {}
        }
        
        # Get test results for this module
        for test in module.tests:
            result = test.get_user_result(current_user.id)
            if result:
                module_data['test_results'][test.id] = result
        
        modules.append(module_data)
    
    # Count total modules and tests
    modules_count = course.modules.count()
    tests_count = db.session.query(Test).join(Module).filter(Module.course_id == course_id).count()
    
    return render_template('view_course.html', 
                         course=course,
                         is_enrolled=is_enrolled,
                         is_author=is_author,
                         modules=modules,
                         modules_count=modules_count,
                         tests_count=tests_count,
                         course_progress=course_progress,
                         enrollment=enrollment)

@app.route('/course/<int:course_id>/enroll', methods=['POST'])
@login_required
def enroll_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if already enrolled
    if Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first():
        return redirect(url_for('view_course', course_id=course_id))
    
    enrollment = Enrollment(user_id=current_user.id, course_id=course_id, start_time=datetime.utcnow())
    db.session.add(enrollment)
    db.session.commit()
    
    return redirect(url_for('view_course', course_id=course_id))

@app.route('/course/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if the current user is the course author
    if course.author_id != current_user.id:
        return redirect(url_for('view_course', course_id=course_id))
    
    if request.method == 'POST':
        course.title = request.form.get('title')
        course.description = request.form.get('description')
        
        # Handle image upload
        if 'image' in request.files:
            image = request.files['image']
            if image.filename:
                filename = f"course_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image.filename}"
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(image_path)
                course.image_path = os.path.join('uploads', filename)
        
        db.session.commit()
        return redirect(url_for('view_course', course_id=course_id))
    
    return render_template('edit_course.html', course=course)

@app.route('/course/<int:course_id>/add_module', methods=['GET', 'POST'])
@login_required
def add_module(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if the current user is the course author
    if course.author_id != current_user.id:
        return redirect(url_for('view_course', course_id=course_id))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        existing_modules = course.modules.all()
        order = len(existing_modules) + 1
        
        new_module = Module(title=title, content=content, course_id=course_id, order=order)
        db.session.add(new_module)
        db.session.commit()
        
        return redirect(url_for('edit_course', course_id=course_id))
    
    return render_template('add_module.html', course=course)

@app.route('/module/<int:module_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_module(module_id):
    module = Module.query.get_or_404(module_id)
    
    # Check if the current user is the course author
    if module.course.author_id != current_user.id:
        return redirect(url_for('view_course', course_id=module.course_id))
    
    if request.method == 'POST':
        module.title = request.form.get('title')
        module.content = request.form.get('content')
        module.order = int(request.form.get('order'))
        
        db.session.commit()
        return redirect(url_for('edit_course', course_id=module.course_id))
    
    return render_template('edit_module.html', module=module)

@app.route('/view_module/<int:module_id>')
@login_required
def view_module(module_id):
    module = Module.query.get_or_404(module_id)
    course = module.course
    
    # Check if user is enrolled or is the author
    enrollment = None
    if current_user.id == course.author_id:
        is_authorized = True
    else:
        enrollment = Enrollment.query.filter_by(
            user_id=current_user.id, 
            course_id=course.id
        ).first()
        is_authorized = enrollment is not None
    
    if not is_authorized:
        return redirect(url_for('view_course', course_id=course.id))
    
    # Update last accessed time for enrollment
    if enrollment:
        enrollment.last_accessed = datetime.utcnow()
        db.session.commit()
    
    # Mark module as viewed
    progress = ModuleProgress.query.filter_by(
        module_id=module_id,
        user_id=current_user.id
    ).first()
    
    if not progress:
        progress = ModuleProgress(
            module_id=module_id,
            user_id=current_user.id,
            completed=False,
            completed_at=datetime.utcnow()
        )
        db.session.add(progress)
        db.session.commit()
    
    # Get test results for this module's tests
    test_results = {}
    module_tests = Test.query.filter_by(module_id=module_id).all()
    
    all_tests_passed = True
    for test in module_tests:
        result = test.get_user_result(current_user.id)
        if result:
            test_results[test.id] = result
            if result.score < 70:
                all_tests_passed = False
        else:
            all_tests_passed = False
    
    if module_tests and all_tests_passed:
        progress.completed = True
        progress.completed_at = datetime.utcnow()
        db.session.commit()
    elif not module_tests:
        progress.completed = True
        progress.completed_at = datetime.utcnow()
        db.session.commit()
    
    # Update course progress
    if enrollment:
        enrollment.progress = course.get_progress(current_user.id)
        db.session.commit()
    
    return render_template('view_module.html', 
                         module=module, 
                         course=course,
                         enrollment=enrollment,
                         test_results=test_results,
                         current_user=current_user)

@app.route('/module/<int:module_id>')
@login_required
def old_view_module(module_id):
    module = Module.query.get_or_404(module_id)
    course = module.course
    
    if not (current_user.id == course.author_id or 
            Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()):
        return redirect(url_for('view_course', course_id=course.id))
    
    return render_template('view_module.html', module=module, course=course)

@app.route('/test/<int:test_id>')
@login_required
def take_test(test_id):
    test = Test.query.get_or_404(test_id)
    return render_template('take_test.html', test=test)

@app.route('/submit_test/<int:test_id>', methods=['POST'])
@login_required
def submit_test(test_id):
    try:
        logger = logging.getLogger(__name__)
        logger.debug(f'Начало submit_test для test_id: {test_id}')
        
        test = Test.query.get_or_404(test_id)
        logger.debug(f'Найден тест: {test.title}')
        
        questions = list(test.questions)
        logger.debug(f'Количество вопросов: {len(questions)}')
        
        if not questions:
            logger.warning(f'В тесте {test.title} нет вопросов')
            return redirect(url_for('view_module', module_id=test.module_id))
        
        correct_answers = 0
        total_questions = len(questions)
        
        for question in questions:
            user_answer = request.form.get(f'answer_{question.id}')
            logger.debug(f'Вопрос {question.id}: ответ пользователя - {user_answer}, правильный ответ - {question.correct_answer}')
            
            if user_answer == question.correct_answer:
                correct_answers += 1
        
        if total_questions > 0:
            score = (correct_answers / total_questions) * 100
        else:
            score = 0
        
        logger.debug(f'Результат теста: {score}% ({correct_answers}/{total_questions})')
        
        existing_result = TestResult.query.filter_by(
            user_id=current_user.id, 
            test_id=test_id
        ).first()
        
        try:
            if existing_result:
                existing_result.score = score
                existing_result.total_questions = total_questions
                existing_result.correct_answers = correct_answers
                existing_result.percentage = score
                existing_result.completed_at = datetime.utcnow()
                logger.debug('Обновлен существующий результат теста')
            else:
                test_result = TestResult(
                    user_id=current_user.id,
                    test_id=test_id,
                    score=score,
                    total_questions=total_questions,
                    correct_answers=correct_answers,
                    percentage=score
                )
                db.session.add(test_result)
                logger.debug('Создан новый результат теста')
            
            db.session.commit()
            logger.debug('Результат теста сохранен')
        except Exception as db_error:
            db.session.rollback()
            logger.error(f'Ошибка при сохранении результата теста: {str(db_error)}')
            raise
        
        if score >= 70:
            try:
                module_progress = ModuleProgress.query.filter_by(
                    module_id=test.module_id,
                    user_id=current_user.id
                ).first()
                
                if not module_progress:
                    module_progress = ModuleProgress(
                        module_id=test.module_id,
                        user_id=current_user.id,
                        completed=True,
                        completed_at=datetime.utcnow()
                    )
                    db.session.add(module_progress)
                else:
                    module_progress.completed = True
                    module_progress.completed_at = datetime.utcnow()
                
                db.session.commit()
                logger.debug('Прогресс модуля обновлен')
            except Exception as module_error:
                db.session.rollback()
                logger.error(f'Ошибка при обновлении прогресса модуля: {str(module_error)}')
                raise
        
        try:
            enrollment = Enrollment.query.filter_by(
                user_id=current_user.id,
                course_id=test.module.course_id
            ).first()
            
            if enrollment:
                enrollment.last_accessed = datetime.utcnow()
                enrollment.end_time = datetime.utcnow()  # Set end time when test is submitted
                db.session.commit()
                logger.debug('Прогресс курса обновлен')
        except Exception as enrollment_error:
            db.session.rollback()
            logger.error(f'Ошибка при обновлении прогресса курса: {str(enrollment_error)}')
            raise
        
        return redirect(url_for('view_module', module_id=test.module_id))
        
    except Exception as e:
        logger.error(f'Критическая ошибка в submit_test: {str(e)}', exc_info=True)
        db.session.rollback()
        return redirect(url_for('view_module', module_id=test.module_id))

@app.route('/my_courses')
@login_required
def my_courses():
    authored_courses = Course.query.filter_by(author_id=current_user.id).all()
    enrolled_courses = Course.query.join(Enrollment).filter(Enrollment.user_id == current_user.id).all()
    
    return render_template('my_courses.html', 
                         authored_courses=authored_courses,
                         enrolled_courses=enrolled_courses)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    app.run(debug=True)