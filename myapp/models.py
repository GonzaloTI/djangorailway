
from django.conf import settings  # Import to get the user model
from django.db import models
from django.contrib.auth.models import AbstractUser #, Group, Permission

class CustomUser(AbstractUser):
    # Your custom user model code
    
    # I Added related_name to avoid clashes with the default User model
    # ManyToManyField was setup for the CustomUser model to associate Groups and Permissions explicitly.
    # im using 'related_name' to prevent clashes.
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="custom_user_set",
        related_query_name="custom_user",
        blank=True,
        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="custom_user_set",
        related_query_name="custom_user",
        blank=True,
        help_text="Specific permissions for this user.",
    )

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre
class Persona(models.Model):
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    sexo = models.CharField(max_length=10, blank=True, null=True)
    fnac = models.DateField(blank=True, null=True)  # Fecha de nacimiento
    telefono = models.CharField(max_length=15, blank=True, null=True)
    rol = models.CharField(max_length=50, blank=True, null=True)
    especialidad = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} {self.apellidos}"
    
class Test(models.Model):
    nombre = models.CharField(max_length=100)
    fecha = models.DateField()
    fecha_entrega = models.DateField()
    estado = models.CharField(max_length=50)
    observaciones = models.TextField(blank=True, null=True)
    calificacion = models.IntegerField()  # Puntuación entre 1 y 10
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    
    # Relación hacia el modelo Persona
    cliente = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="tests_como_cliente")
    personal = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="tests_como_personal")


    def __str__(self):
        return self.nombre

class Resultado(models.Model):
    test = models.OneToOneField(Test, on_delete=models.CASCADE)  # Relación uno a uno con Test
    resultado = models.CharField(max_length=100)
    fecha = models.DateField()
    observaciones = models.TextField(blank=True, null=True)
    interpretacion = models.TextField(blank=True, null=True)
    detalles = models.TextField(blank=True, null=True)
    url_imagen_path = models.URLField(blank=True, null=True)  # URL de la imagen (opcional)

    def __str__(self):
        return f"Resultado de {self.test.nombre}"
    
