# 📚 Bookglance - Tienda Online

Tienda online con sistema de caja POS.

## 🚀 Despliegue en Render

1. **Crear cuenta** en [render.com](https://render.com)

2. **Crear base de datos PostgreSQL**:
   - Dashboard → "New" → "PostgreSQL"
   - Nombre: `bookglance-db`
   - Guardar la URL de conexión

3. **Crear Web Service**:
   - "New" → "Web Service"
   - Conectar tu repositorio GitHub
   - Build Command: (vacío)
   - Start Command: `gunicorn app:app`
   - Environment Variables:
     - `DATABASE_URL`: pegar la URL de PostgreSQL

4. **Subir imágenes**:
   - Los productos necesitan imágenes en la carpeta `static/images`
   - Podés usar el panel de Render o un bucket externo (Cloudinary)

## 🖥️ Desarrollo local

```bash
# Instalar dependencias
pip install -r requirement.txt

# Ejecutar
python app.py
```

## 👤 Login

- Admin: `admin` / `1234`