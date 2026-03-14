from flask import Blueprint, render_template, request, redirect, session, flash, url_for
import requests
from config import Config

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    return redirect(url_for('auth.login_page'))

@auth_bp.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    login = request.form.get('login')
    password = request.form.get('password')
    
    if not login or not password:
        flash('Введите логин и пароль')
        return redirect(url_for('auth.login_page'))
    
    try:
        url = f"{Config.SUPABASE_URL}/rest/v1/users"
        headers = {
            'apikey': Config.SUPABASE_KEY,
            'Authorization': f'Bearer {Config.SUPABASE_KEY}'
        }
        params = {'login': f'eq.{login}'}
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            flash('Ошибка подключения к базе данных')
            return redirect(url_for('auth.login_page'))
        
        data = response.json()
        
        if len(data) == 0:
            flash('Пользователь не найден')
            return redirect(url_for('auth.login_page'))
        
        user = data[0]
        
        if user['password'] != password:
            flash('Неверный пароль')
            return redirect(url_for('auth.login_page'))
        
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['user_role'] = user['role']
        
        if user['role'] == 'Администратор':
            return redirect('/admin/products')  
        elif user['role'] == 'Менеджер':
            return redirect('/orders')
        else:
            return redirect('/catalog')
            
    except Exception as e:
        flash(f'Ошибка: {str(e)}')
        return redirect(url_for('auth.login_page'))

@auth_bp.route('/guest')
def guest_login():
    session['user_role'] = 'Гость'
    session['user_name'] = 'Гость'
    return redirect('/catalog')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login_page'))
