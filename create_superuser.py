from django.contrib.auth import get_user_model

User = get_user_model()

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@mynba360.com',
        password='admin123'
    )
    print("✔ Superusuario creado correctamente")
else:
    print("ℹ Superusuario ya existe")