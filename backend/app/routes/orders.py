from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from config import Config
import requests
from datetime import datetime

orders_bp = Blueprint('orders', __name__)

def is_admin():
    return session.get('user_role') == 'Администратор'

def is_manager_or_admin():
    role = session.get('user_role')
    return role in ['Менеджер', 'Администратор']

# Страница со списком заказов (для менеджера и админа)
@orders_bp.route('/orders')
def orders_list():
    if not is_manager_or_admin():
        flash('Доступ запрещён')
        return redirect(url_for('auth.login_page'))
    
    headers = {
        'apikey': Config.SUPABASE_KEY,
        'Authorization': f'Bearer {Config.SUPABASE_KEY}',
        'Accept': 'application/json'
    }
    
    try:
        # Один запрос для получения всех заказов с клиентами и пунктами выдачи
        url = f"{Config.SUPABASE_URL}/rest/v1/orders?select=*,users(full_name,login),pickup_points(address)"
        
        response = requests.get(url, headers=headers)
        orders = response.json()
        
        # Для каждого заказа получаем состав и товары (можно тоже оптимизировать)
        for order in orders:
            # Получаем состав заказа с товарами
            items_url = f"{Config.SUPABASE_URL}/rest/v1/order_items?order_id=eq.{order['id']}&select=*,products(name,price,discount)"
            items_resp = requests.get(items_url, headers=headers)
            items = items_resp.json()
            
            # Считаем сумму
            total = 0
            for item in items:
                if 'products' in item:
                    product = item['products']
                    price = product['price'] * (100 - product.get('discount', 0)) / 100
                    total += price * item['quantity']
                    item['product_name'] = product['name']
            
            order['items'] = items
            order['total'] = total
            order['client_name'] = order.get('users', {}).get('full_name', 'Не указан')
            order['pickup_address'] = order.get('pickup_points', {}).get('address', 'Не указан')
        
        return render_template('orders.html', orders=orders, is_admin=is_admin())
        
    except Exception as e:
        flash(f'Ошибка загрузки заказов: {str(e)}')
        return redirect(url_for('products.catalog'))

# Просмотр одного заказа (детали)
@orders_bp.route('/orders/<int:order_id>')
def order_detail(order_id):
    if not is_manager_or_admin():
        flash('Доступ запрещён')
        return redirect(url_for('auth.login_page'))
    
    headers = {
        'apikey': Config.SUPABASE_KEY,
        'Authorization': f'Bearer {Config.SUPABASE_KEY}'
    }
    
    try:
        # Получаем заказ
        url = f"{Config.SUPABASE_URL}/rest/v1/orders?id=eq.{order_id}"
        response = requests.get(url, headers=headers)
        
        if not response.json():
            flash('Заказ не найден')
            return redirect(url_for('orders.orders_list'))
            
        order = response.json()[0]
        
        # Получаем клиента
        if order.get('user_id'):
            user_url = f"{Config.SUPABASE_URL}/rest/v1/users?id=eq.{order['user_id']}"
            user_resp = requests.get(user_url, headers=headers)
            if user_resp.json():
                order['client'] = user_resp.json()[0]
        
        # Получаем пункт выдачи
        if order.get('pickup_point_id'):
            point_url = f"{Config.SUPABASE_URL}/rest/v1/pickup_points?id=eq.{order['pickup_point_id']}"
            point_resp = requests.get(point_url, headers=headers)
            if point_resp.json():
                order['pickup_point'] = point_resp.json()[0]
        
        # Получаем состав заказа
        items_url = f"{Config.SUPABASE_URL}/rest/v1/order_items?order_id=eq.{order_id}&select=*"
        items_resp = requests.get(items_url, headers=headers)
        items = items_resp.json()
        
        # Для каждого товара получаем детали и считаем общую сумму
        total_sum = 0
        for item in items:
            product_url = f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{item['product_id']}"
            product_resp = requests.get(product_url, headers=headers)
            
            if product_resp.json():
                product = product_resp.json()[0]
                item['product'] = product
                # Цена со скидкой
                price_with_discount = product['price'] * (100 - product['discount']) / 100
                item['price_with_discount'] = price_with_discount
                # Добавляем в общую сумму
                total_sum += price_with_discount * item['quantity']
            else:
                item['price_with_discount'] = 0
        
        # 👇 ОТЛАДКА (можно удалить после проверки)
        print("="*50)
        print(f"ORDER: {order}")
        print(f"ITEMS: {items}")
        print(f"TOTAL SUM: {total_sum}")
        print("="*50)
        # 👆 КОНЕЦ ОТЛАДКИ
        
        return render_template(
            'order_detail.html', 
            order=order, 
            items=items, 
            is_admin=is_admin(),
            total=total_sum  # ← передаём отдельно
        )
        
    except Exception as e:
        flash(f'Ошибка загрузки заказа: {str(e)}')
        return redirect(url_for('orders.orders_list'))

# Создание нового заказа (только админ)
@orders_bp.route('/orders/create', methods=['GET', 'POST'])
def create_order():
    if not is_admin():
        flash('Доступ запрещён')
        return redirect(url_for('auth.login_page'))
    
    headers = {
        'apikey': Config.SUPABASE_KEY,
        'Authorization': f'Bearer {Config.SUPABASE_KEY}'
    }
    
    if request.method == 'POST':
        # Получаем данные из формы
        user_id = request.form.get('user_id')
        pickup_point_id = request.form.get('pickup_point_id')
        delivery_date = request.form.get('delivery_date')
        status = request.form.get('status', 'Новый')
        
        # Создаём заказ
        order_url = f"{Config.SUPABASE_URL}/rest/v1/orders"
        order_data = {
            'order_number': int(datetime.now().timestamp()),  # временный номер
            'user_id': int(user_id) if user_id else None,
            'order_date': datetime.now().isoformat(),
            'delivery_date': delivery_date,
            'pickup_point_id': int(pickup_point_id) if pickup_point_id else None,
            'status': status,
            'pickup_code': str(int(datetime.now().timestamp()))[-6:]  # последние 6 цифр
        }
        
        try:
            response = requests.post(order_url, headers=headers, json=order_data)
            if response.status_code in [200, 201]:
                flash('Заказ создан')
                return redirect(url_for('orders.orders_list'))
            else:
                flash(f'Ошибка: {response.text}')
        except Exception as e:
            flash(f'Ошибка: {str(e)}')
        
        return redirect(url_for('orders.orders_list'))
    
    # GET — показываем форму
    # Получаем список клиентов и пунктов выдачи для выпадающих списков
    users = requests.get(f"{Config.SUPABASE_URL}/rest/v1/users", headers=headers).json()
    points = requests.get(f"{Config.SUPABASE_URL}/rest/v1/pickup_points", headers=headers).json()
    
    return render_template('order_form.html', users=users, points=points, order=None)

# Редактирование заказа (только админ)
@orders_bp.route('/orders/edit/<int:order_id>', methods=['GET', 'POST'])
def edit_order(order_id):
    if not is_admin():
        flash('Доступ запрещён')
        return redirect(url_for('auth.login_page'))
    
    headers = {
        'apikey': Config.SUPABASE_KEY,
        'Authorization': f'Bearer {Config.SUPABASE_KEY}'
    }
    
    if request.method == 'POST':
        # Обновляем заказ
        url = f"{Config.SUPABASE_URL}/rest/v1/orders?id=eq.{order_id}"
        data = {
            'user_id': int(request.form.get('user_id')) if request.form.get('user_id') else None,
            'pickup_point_id': int(request.form.get('pickup_point_id')) if request.form.get('pickup_point_id') else None,
            'delivery_date': request.form.get('delivery_date'),
            'status': request.form.get('status')
        }
        
        try:
            response = requests.patch(url, headers=headers, json=data)
            if response.status_code == 200:
                flash('Заказ обновлён')
            else:
                flash(f'Ошибка: {response.text}')
        except Exception as e:
            flash(f'Ошибка: {str(e)}')
        
        return redirect(url_for('orders.orders_list'))
    
    # GET — получаем данные заказа
    order_url = f"{Config.SUPABASE_URL}/rest/v1/orders?id=eq.{order_id}"
    order = requests.get(order_url, headers=headers).json()[0]
    
    users = requests.get(f"{Config.SUPABASE_URL}/rest/v1/users", headers=headers).json()
    points = requests.get(f"{Config.SUPABASE_URL}/rest/v1/pickup_points", headers=headers).json()
    
    return render_template('order_form.html', order=order, users=users, points=points)

# Удаление заказа (только админ)
@orders_bp.route('/orders/delete/<int:order_id>')
def delete_order(order_id):
    if not is_admin():
        flash('Доступ запрещён')
        return redirect(url_for('auth.login_page'))
    
    headers = {
        'apikey': Config.SUPABASE_KEY,
        'Authorization': f'Bearer {Config.SUPABASE_KEY}'
    }
    
    try:
        # Сначала удаляем связанные позиции
        items_url = f"{Config.SUPABASE_URL}/rest/v1/order_items?order_id=eq.{order_id}"
        requests.delete(items_url, headers=headers)
        
        # Потом сам заказ
        order_url = f"{Config.SUPABASE_URL}/rest/v1/orders?id=eq.{order_id}"
        response = requests.delete(order_url, headers=headers)
        
        if response.status_code == 200:
            flash('Заказ удалён')
        else:
            flash('Ошибка при удалении')
    except Exception as e:
        flash(f'Ошибка: {str(e)}')
    
    return redirect(url_for('orders.orders_list'))

# Изменение статуса заказа (для менеджера и админа)
@orders_bp.route('/orders/status/<int:order_id>', methods=['POST'])
def change_status(order_id):
    if not is_manager_or_admin():
        flash('Доступ запрещён')
        return redirect(url_for('auth.login_page'))
    
    new_status = request.form.get('status')
    
    headers = {
        'apikey': Config.SUPABASE_KEY,
        'Authorization': f'Bearer {Config.SUPABASE_KEY}'
    }
    
    url = f"{Config.SUPABASE_URL}/rest/v1/orders?id=eq.{order_id}"
    data = {'status': new_status}
    
    try:
        response = requests.patch(url, headers=headers, json=data)
        if response.status_code == 200:
            flash('Статус обновлён')
        else:
            flash('Ошибка обновления статуса')
    except Exception as e:
        flash(f'Ошибка: {str(e)}')
    
    return redirect(url_for('orders.orders_list'))