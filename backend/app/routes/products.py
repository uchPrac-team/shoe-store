from flask import Blueprint, render_template, session, request, flash, redirect, url_for
from config import Config
import requests

products_bp = Blueprint('products', __name__)

def get_user_role():
    """Получить роль текущего пользователя"""
    return session.get('user_role', 'Гость')

@products_bp.route('/catalog')
def catalog():
    """Страница каталога товаров"""
    role = get_user_role()
    
    # Получаем параметры фильтрации и сортировки
    category = request.args.get('category', '')
    sort_by = request.args.get('sort', 'name')
    search = request.args.get('search', '')
    
    # Запрос к Supabase
    url = f"{Config.SUPABASE_URL}/rest/v1/products"
    headers = {
        'apikey': Config.SUPABASE_KEY,
        'Authorization': f'Bearer {Config.SUPABASE_KEY}'
    }
    
    # Базовый запрос
    params = {
        'select': '*',
        'order': sort_by
    }
    
    # Добавляем фильтры (только для менеджера и админа)
    if role in ['Менеджер', 'Администратор']:
        if category:
            params['category'] = f'eq.{category}'
        if search:
            params['name'] = f'ilike.%{search}%'
    
    try:
        response = requests.get(url, headers=headers, params=params)
        products = response.json()
        
        # Получаем список категорий для фильтра
        categories_url = f"{Config.SUPABASE_URL}/rest/v1/products?select=category"
        cat_response = requests.get(categories_url, headers=headers)
        categories = list(set([p['category'] for p in cat_response.json() if p['category']]))
        
        return render_template(
            'catalog.html',
            products=products,
            categories=categories,
            role=role,
            current_category=category,
            current_sort=sort_by,
            current_search=search
        )
    except Exception as e:
        return f"Ошибка загрузки товаров: {str(e)}"

@products_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    """Страница отдельного товара"""
    headers = {
        'apikey': Config.SUPABASE_KEY,
        'Authorization': f'Bearer {Config.SUPABASE_KEY}'
    }
    
    try:
        # Получаем товар по ID
        url = f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}"
        response = requests.get(url, headers=headers)
        
        if not response.json():
            flash('Товар не найден')
            return redirect(url_for('products.catalog'))
        
        product = response.json()[0]
        role = get_user_role()
        
        return render_template('product_detail.html', product=product, role=role)
        
    except Exception as e:
        flash(f'Ошибка загрузки товара: {str(e)}')
        return redirect(url_for('products.catalog'))