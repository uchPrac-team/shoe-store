from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from config import Config
import requests
import os
from werkzeug.utils import secure_filename

admin_products_bp = Blueprint('admin_products', __name__)

# Разрешённые расширения файлов
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_admin():
    return session.get('user_role') == 'Администратор'

# Страница управления товарами
@admin_products_bp.route('/admin/products')
def admin_products():
    if not is_admin():
        flash('Доступ запрещён')
        return redirect(url_for('auth.login_page'))
    
    # Получаем все товары
    url = f"{Config.SUPABASE_URL}/rest/v1/products"
    headers = {
        'apikey': Config.SUPABASE_KEY,
        'Authorization': f'Bearer {Config.SUPABASE_KEY}'
    }
    
    try:
        response = requests.get(url, headers=headers)
        products = response.json()
        return render_template('admin_products.html', products=products)
    except Exception as e:
        flash(f'Ошибка загрузки: {str(e)}')
        return redirect(url_for('products.catalog'))

# Добавление товара
@admin_products_bp.route('/admin/products/add', methods=['GET', 'POST'])
def add_product():
    if not is_admin():
        flash('Доступ запрещён')
        return redirect(url_for('auth.login_page'))
    
    if request.method == 'POST':
        # Получаем данные из формы
        article = request.form.get('article')
        name = request.form.get('name')
        price = request.form.get('price')
        category = request.form.get('category')
        supplier = request.form.get('supplier')
        manufacturer = request.form.get('manufacturer')
        discount = request.form.get('discount', 0)
        stock = request.form.get('stock', 0)
        description = request.form.get('description')
        
        # Обработка фото
        photo = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Сохраняем файл
                file.save(os.path.join('app/static/images', filename))
                photo = filename
        
        # Отправляем в Supabase
        url = f"{Config.SUPABASE_URL}/rest/v1/products"
        headers = {
            'apikey': Config.SUPABASE_KEY,
            'Authorization': f'Bearer {Config.SUPABASE_KEY}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }
        
        data = {
            'article': article,
            'name': name,
            'price': float(price),
            'category': category,
            'supplier': supplier,
            'manufacturer': manufacturer,
            'discount': int(discount),
            'stock': int(stock),
            'description': description,
            'photo': photo
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code in [200, 201]:
                flash('Товар успешно добавлен')
            else:
                flash(f'Ошибка при добавлении: {response.text}')
        except Exception as e:
            flash(f'Ошибка: {str(e)}')
        
        return redirect(url_for('admin_products.admin_products'))
    
    return render_template('product_form.html', product=None)

# Редактирование товара
@admin_products_bp.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if not is_admin():
        flash('Доступ запрещён')
        return redirect(url_for('auth.login_page'))
    
    headers = {
        'apikey': Config.SUPABASE_KEY,
        'Authorization': f'Bearer {Config.SUPABASE_KEY}'
    }
    
    if request.method == 'POST':
        # Обновляем товар
        url = f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}"
        
        data = {
            'article': request.form.get('article'),
            'name': request.form.get('name'),
            'price': float(request.form.get('price')),
            'category': request.form.get('category'),
            'supplier': request.form.get('supplier'),
            'manufacturer': request.form.get('manufacturer'),
            'discount': int(request.form.get('discount', 0)),
            'stock': int(request.form.get('stock', 0)),
            'description': request.form.get('description')
        }
        
        # Обработка нового фото
        if 'photo' in request.files:
            file = request.files['photo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join('app/static/images', filename))
                data['photo'] = filename
        
        try:
            response = requests.patch(url, headers=headers, json=data)
            if response.status_code == 200:
                flash('Товар обновлён')
            else:
                flash(f'Ошибка обновления: {response.text}')
        except Exception as e:
            flash(f'Ошибка: {str(e)}')
        
        return redirect(url_for('admin_products.admin_products'))
    
    # GET — показываем форму с данными товара
    url = f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}"
    try:
        response = requests.get(url, headers=headers)
        product = response.json()[0]
        return render_template('product_form.html', product=product)
    except Exception as e:
        flash(f'Ошибка загрузки товара: {str(e)}')
        return redirect(url_for('admin_products.admin_products'))

# Удаление товара
@admin_products_bp.route('/admin/products/delete/<int:product_id>')
def delete_product(product_id):
    if not is_admin():
        flash('Доступ запрещён')
        return redirect(url_for('auth.login_page'))
    
    url = f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}"
    headers = {
        'apikey': Config.SUPABASE_KEY,
        'Authorization': f'Bearer {Config.SUPABASE_KEY}'
    }
    
    try:
        response = requests.delete(url, headers=headers)
        if response.status_code == 200:
            flash('Товар удалён')
        else:
            flash('Ошибка при удалении')
    except Exception as e:
        flash(f'Ошибка: {str(e)}')
    
    return redirect(url_for('admin_products.admin_products'))