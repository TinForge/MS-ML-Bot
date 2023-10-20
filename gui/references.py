# All assets referenced here

import PIL.Image
import PIL.ImageTk

app_icon = "resources/mushroom icon.png"
mushroom_image = "resources/mushroom 256.png"
mushroom_animated = "resources/mushroom animated.gif"

green_circle = PIL.Image.open("resources/green circle.png").resize((10, 10))
red_circle = PIL.Image.open("resources/red circle.png").resize((10, 10))

green_icon = None
red_icon = None

var_font = ("Open Sans", 10)


def initialize_images():
    global green_icon, red_icon
    green_icon = PIL.ImageTk.PhotoImage(green_circle)
    red_icon = PIL.ImageTk.PhotoImage(red_circle)
