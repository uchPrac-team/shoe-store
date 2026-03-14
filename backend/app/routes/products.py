from flask import Blueprint, render_template, session, request
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

# Временные заглушки для страниц админа и менеджера
@products_bp.route('/admin')
def admin():
    return "Страница администратора (в разработке)"

@products_bp.route('/manager')
def manager():
    return "Страница менеджера (в разработке)"