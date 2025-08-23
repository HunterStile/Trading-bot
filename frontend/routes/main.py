from flask import Blueprint, render_template, send_from_directory, current_app

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def dashboard():
    """Dashboard principale"""
    return render_template('dashboard.html')

@main_bp.route('/control')
def bot_control():
    """Pagina di controllo del bot"""
    bot_status = current_app.config['BOT_STATUS']
    return render_template('bot_control.html', bot_status=bot_status)

@main_bp.route('/api-test')
def api_test():
    """Pagina per testare le API"""
    return render_template('api_test.html')

@main_bp.route('/settings')
def settings():
    """Pagina delle impostazioni"""
    bot_status = current_app.config['BOT_STATUS']
    return render_template('settings.html', bot_status=bot_status)

@main_bp.route('/history')
def history_page():
    """Pagina storico trading"""
    return render_template('history.html')

@main_bp.route('/history-simple')
def history_simple_page():
    """Pagina storico trading semplificata"""
    return render_template('history_simple.html')

@main_bp.route('/debug')
def debug_page():
    """Pagina debug per testare API"""
    return send_from_directory('.', 'debug_history.html')

@main_bp.route('/ultra')
def ultra_simple_page():
    """Pagina ultra semplice per storico"""
    return send_from_directory('.', 'ultra_simple_history.html')