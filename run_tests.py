import unittest
import sys
import os

def run_all_tests():
    """Запускає всі тести у директорії tests/"""
    print("=== ЗАПУСК МОДУЛЬНИХ ТЕСТІВ ===")
    
    # Додаємо теку src до sys.path для коректного імпорту
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    # Пошук та запуск тестів
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir='tests', pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Повертаємо код 0 (успіх) або 1 (помилка) для CLI/CI
    sys.exit(not result.wasSuccessful())

if __name__ == '__main__':
    run_all_tests()