import win32gui

# Represents global variables for app
app_found = False
app_focus = False


# Updates per frame
def Refresh():
    global app_found
    global app_focus
    app_found = win32gui.FindWindow(None, "MapleLegends (Nov 6 2022)") == 0
    app_focus = False
