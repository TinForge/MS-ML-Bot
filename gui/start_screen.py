# Launch screen for Maplestory ML Bot
import gooeypie as gp
import main_screen
import references


def main():
    def on_clicked(event):
        app.exit()
        main_screen.main()

    app = gp.GooeyPieApp("Launcher")
    app.set_icon(references.app_icon)
    app.set_resizable(False)
    app.width = 350

    header = gp.Label(app, "Welcome to Maplestory ML Bot")
    body = gp.Label(app, "Developed by Wei")
    image = gp.Image(app, references.mushroom_image)
    button = gp.Button(app, "Launch", on_clicked)

    app.set_grid(4, 1)
    app.add(header, 1, 1, align="center")
    app.add(body, 2, 1, align="center")
    app.add(image, 3, 1, align="center")
    app.add(button, 4, 1, align="center")
    app.run()


if __name__ == "__main__":
    print("Launching Start Screen...")
    main()