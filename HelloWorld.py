#! /usr/bin/env python3

import sys

from PyQt5.QtWidgets import QApplication, QWidget

app = None

def main():

    global app
    app = QApplication(sys.argv)

    widget = QWidget()
    widget.setWindowTitle("Hello, World!")
    widget.show()

    print("Qt is now handling everything!")
    app.exec_()
    print("Qt is done.")

if __name__ == "__main__":
    main()
