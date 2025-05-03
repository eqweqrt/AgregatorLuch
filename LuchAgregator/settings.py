import os
from pathlib import Path
import dj_database_url
# Импортируем load_dotenv для загрузки из .env и set_key для записи в .env
from dotenv import load_dotenv, set_key

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['luch-it.space','www.luch-it.space','92.242.60.140']


# Application definition

# === Сначала определяем путь к .env файлу и загружаем существующие переменные ===
dotenv_path = BASE_DIR / '.env'
load_dotenv(dotenv_path) # Загружаем переменные из .env, если файл существует


# SECURITY WARNING: keep the secret key used in production secret!
# УДАЛЯЕМ хардкодный SECRET_KEY
# SECRET_KEY = 'django-insecure-(&d)ye32^%%#6z4f57k!g7oaxv+g7xod@)u)l^ou$_^0!-9&p%'

# === Проверка и генерация SECRET_KEY ===
SECRET_KEY = os.environ.get('SECRET_KEY')

if not SECRET_KEY:
    # SECRET_KEY не найден в переменных окружения (включая загруженные из .env)
    if DEBUG:
        # Генерируем новый SECRET_KEY только в режиме DEBUG
        try:
            # Генерируем криптографически стойкий ключ
            generated_key = os.urandom(32).hex()
            SECRET_KEY = generated_key
            print("Generated a new SECRET_KEY for local DEBUG.")

            # Попытка сохранить ключ в .env файл
            try:
                # Создаем файл .env, если его нет, или открываем для добавления/изменения
                if not dotenv_path.exists():
                     dotenv_path.touch() # Создать файл, если он не существует
                     print(f"Created .env file at {dotenv_path}")

                # Используем set_key для безопасной записи/обновления ключа в .env
                # set_key сохранит ключ в файле в формате KEY=Value
                set_key(dotenv_path, 'SECRET_KEY', SECRET_KEY)
                print(f"Saved SECRET_KEY to {dotenv_path}")

                # Опционально, можно снова загрузить, хотя set_key обычно обновляет os.environ
                # load_dotenv(dotenv_path)
                # os.environ['SECRET_KEY'] = SECRET_KEY # Убедимся, что в текущем процессе переменная установлена

            except Exception as e:
                # Если сохранить не удалось (например, нет прав записи), выводим предупреждение
                print(f"WARNING: Could not save SECRET_KEY to {dotenv_path}. Please add 'SECRET_KEY={SECRET_KEY}' manually to your .env file or environment variables. Error: {e}")
                # Приложение продолжит работать с этим сгенерированным ключом в текущем процессе

        except Exception as e:
             # Если генерация ключа вызвала ошибку (очень маловероятно)
             print(f"FATAL ERROR: Could not generate SECRET_KEY: {e}")
             # В этом случае SECRET_KEY останется None, и Django вызовет ошибку позже.


    else:
        # В режиме PRODUCTION, SECRET_KEY ДОЛЖЕН быть установлен как переменная окружения
        # Если его нет, вызываем фатальную ошибку, чтобы приложение не запустилось
        raise EnvironmentError("FATAL: SECRET_KEY not found in environment variables! This is required for production (DEBUG=False). Please set the SECRET_KEY environment variable.")

# === Проверка, что SECRET_KEY установлен после всех попыток ===
if not SECRET_KEY:
    # Этот случай должен возникать только если генерация в DEBUG не удалась
    # и SECRET_KEY остался None
    raise EnvironmentError("FATAL: SECRET_KEY is not set. Check your .env file, environment variables, or permissions if in DEBUG mode.")


# ====================================================

# ИЗМЕНЕНО: Загружаем ALLOWED_HOSTS из переменной окружения, если она установлена
ALLOWED_HOSTS = ['92.242.60.140', 'luch-it.space', 'www.luch-it.space']


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'catalog',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'LuchAgregator.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Исправлено: используем Path
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'LuchAgregator.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# ИЗМЕНЕНО: Загружаем DATABASE_URL из переменной окружения
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///{}'.format(os.path.join(BASE_DIR, 'db.sqlite3')))
DATABASES ={
	'default':{
		'ENGINE':'django.db.backends.postgresql',
		'NAME':'luchdb',
		'USER':'luchuserdb',
		'PASSWORD':'GTv81Ex6',
		'HOST':'localhost',
		'PORT':'',
	}
}


#Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    BASE_DIR / 'static', # Добавьте вашу папку static в корне проекта
]

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'catalog_selection'
LOGOUT_URL = 'logout'


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO', # Установите на 'ERROR' или 'WARNING' для меньшего объема логов в продакшене
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'django.log', # Имя файла лога на сервере. Убедитесь в правах на запись.
        },
        'console': { # Оставьте, чтобы Gunicorn мог выводить логи в stdout/stderr, которые systemd поймает
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO', # Или WARN/ERROR в продакшене
            'propagate': True,
        },
        # Можно добавить логирование для вашего приложения catalog
        'catalog': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': { # Корневой логгер
        'handlers': ['console'],
        'level': 'WARNING', # Записывать в консоль только WARNING и выше для всего остального
    },
}
