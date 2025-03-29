import multiprocessing  # для организации параллельных процессов
import random  # для генерации случайных чисел
import time    # для имитации времени работы и пауз
import sys     # для работы с аргументами командной строки
import threading  # для запуска потока ввода команды
import queue as Queue  # для безопасной передачи данных между потоками
import signal  # для обработки сигналов прерывания

# функция генерации случайной квадратной матрицы заданного размера
def generate_random_matrix(size):
    # генерирует случайную квадратную матрицу заданного размера. создаем матрицу с помощью вложенных списков
    matrix = []
    for _ in range(size):
        # генерируем строку матрицы
        row = [random.randint(0, 10) for _ in range(size)]
        matrix.append(row)
    return matrix

# процесс-генератор матриц
def matrix_generator(queue, size, stop_event):
    # генерирует пары случайных матриц и отправляет их в очередь для перемножения
    print("запуск процесса генерации матриц.")
    try:
        while not stop_event.is_set():
            # генерируем две случайные матрицы
            A = generate_random_matrix(size)
            B = generate_random_matrix(size)
            # отправляем пару матриц в очередь
            queue.put((A, B))
            print("сгенерированы две матрицы и отправлены в очередь.")
            # имитация задержки между генерациями
            time.sleep(1)
    except KeyboardInterrupt:
        print("процесс генерации матриц прерван.")
    finally:
        # после остановки генерации отправляем специальный сигнал (None) для завершения работы умножителя
        queue.put(None)
        print("остановка процесса генерации матриц.")

# процесс перемножения матриц
def matrix_multiplier(queue, stop_event):
    # получает пары матриц из очереди, перемножает их и записывает результат в файл
    print("Запуск процесса перемножения матриц.")
    try:
        # открываем файл для записи результатов
        with open('multiplication_results.txt', 'w') as result_file:
            while True:
                # проверяем, установлен ли сигнал остановки и пуста ли очередь
                if stop_event.is_set() and queue.empty():
                    break
                try:
                    # устанавливаем таймаут, чтобы можно было проверить stop_event
                    matrices = queue.get(timeout=1)
                except Queue.Empty:
                    continue
                # проверяем специальный сигнал для завершения работы
                if matrices is None:
                    print("получен сигнал завершения умножения.")
                    break
                A, B = matrices
                # проверяем возможность перемножения матриц
                if len(A[0]) != len(B):
                    print("матрицы не могут быть перемножены: число столбцов A не равно числу строк B")
                    continue
                # перемножаем матрицы
                result_matrix = multiply_matrices(A, B)
                # записываем результат в файл
                write_matrix_to_file(result_matrix, result_file)
                print("матрицы перемножены и результат записан в файл.")
    except KeyboardInterrupt:
        print("процесс перемножения матриц прерван.")
    finally:
        print("остановка процесса перемножения матриц.")

# функция перемножения двух матриц
def multiply_matrices(A, B):
    # перемножает две матрицы A и B. число строк и столбцов результирующей матрицы
    result_rows = len(A)
    result_cols = len(B[0])
    # инициализируем результирующую матрицу нулями
    result_matrix = [[0 for _ in range(result_cols)] for _ in range(result_rows)]
    # выполняем умножение матриц
    for i in range(result_rows):
        for j in range(result_cols):
            for k in range(len(B)):
                result_matrix[i][j] += A[i][k] * B[k][j]
    return result_matrix

# функция записи матрицы в файл
def write_matrix_to_file(matrix, file):
    # записывает матрицу в файл
    for row in matrix:
        # преобразуем числа в строки
        str_numbers = [str(num) for num in row]
        # объединяем числа через пробел и добавляем перевод строки
        line = ' '.join(str_numbers) + '\n'
        # записываем строку в файл
        file.write(line)
    # добавляем разделитель между матрицами
    file.write('=' * 20 + '\n')

# функция для обработки пользовательского ввода в отдельном потоке
def user_input_thread(stop_event):
    # ожидает ввода команды 'stop' для остановки программы
    while not stop_event.is_set():
        try:
            command = input("введите 'stop' для остановки программы: ")
            if command.strip().lower() == 'stop':
                stop_event.set()
                print("инициирована остановка программы.")
                break
        except EOFError:
            break
        except KeyboardInterrupt:
            stop_event.set()
            print("\nпрограмма прервана пользователем.")
            break

# функция для обработки сигналов прерывания
def signal_handler(sig, frame):
    print("\nполучен сигнал прерывания. программа завершается.")
    # устанавливаем событие остановки
    global stop_event
    stop_event.set()

# главная функция программы
def main():
    # основная функция программы. глобальное событие остановки
    global stop_event
    stop_event = multiprocessing.Event()

    # устанавливаем обработчик сигналов
    signal.signal(signal.SIGINT, signal_handler)

    # проверяем наличие аргумента командной строки для размерности матриц
    if len(sys.argv) != 2:
        print("использование: python программа.py размерность_матрицы")
        sys.exit(1)
    # получаем размерность матрицы из аргументов командной строки
    try:
        matrix_size = int(sys.argv[1])
    except ValueError:
        print("размерность матрицы должна быть целым числом.")
        sys.exit(1)
    # создаем очередь для передачи матриц между процессами
    queue = multiprocessing.Queue()
    # создаем процессы генерации и умножения матриц
    generator_process = multiprocessing.Process(target=matrix_generator, args=(queue, matrix_size, stop_event))
    multiplier_process = multiprocessing.Process(target=matrix_multiplier, args=(queue, stop_event))
    # запускаем процессы
    generator_process.start()
    multiplier_process.start()
    # запускаем поток для ввода команды от пользователя
    input_thread = threading.Thread(target=user_input_thread, args=(stop_event,))
    input_thread.start()
    # ожидаем завершения потока ввода
    input_thread.join()
    # ожидаем завершения процессов
    generator_process.join()
    multiplier_process.join()
    print("программа завершена.")

# запускаем главную функцию, если скрипт запущен напрямую
if __name__ == '__main__':
    main()