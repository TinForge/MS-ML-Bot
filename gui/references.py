#  file path references
import PIL.Image
import PIL.ImageTk

app_icon = "assets/mushroom icon.png"
mushroom_image = "assets/mushroom 256.png"
mushroom_animated = "assets/mushroom animated.gif"

green_circle = PIL.Image.open("assets/green circle.png").resize((10, 10))
red_circle = PIL.Image.open("assets/red circle.png").resize((10, 10))

green_icon = None
red_icon = None


def initialize_images():
    global green_icon, red_icon
    green_icon = PIL.ImageTk.PhotoImage(green_circle)
    red_icon = PIL.ImageTk.PhotoImage(red_circle)


var_font = ("Open Sans", 10)