# Main screen for Maplestory ML Bot
import gooeypie as gp
import references
import ms_stats


class instance():

    def on_clicked(self):
        self.header.text = "yerrrr"

    def get_values(self):
        ms_stats.Refresh()
        self.app_found.text = ms_stats.app_found

    def __init__(self):
        # initialize
        app = gp.GooeyPieApp("Maple ML Bot")
        app.set_icon(references.app_icon)
        app.set_resizable(False)
        app.width = 350

        # other
        header = gp.Label(app, "This is main window")
        button = gp.Button(app, "Ok", self.on_clicked)


        # status group
        status_group = gp.LabelContainer(app, "Status")
        status_group.set_grid(1, 2)
        status_group.set_column_weights(0, 0)

        # elements
        element1 = gp.Label(status_group, "Maplestory Found:")
        status_group.add(element1, 1, 1, align="center")
        self.app_found = gp.Label(status_group, "-/-")
        status_group.add(self.app_found, 1, 2, align="center")


        app.set_grid(3, 1)
        app.add(header, 1, 1, align="center", fill=True)
        app.add(button, 2, 1, align="center", fill=True)
        app.add(status_group, 3, 1, align="center", valign="bottom")
        app.set_interval(1000, self.get_values)
        app.run()


if __name__ == "__main__":
    print("Launching main screen...")
    instance()