# Crear DB solo una vez, manualmente
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    print("Base de datos inicializada.")
    app.run(debug=True)