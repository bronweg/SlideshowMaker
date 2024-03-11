import sys
import os
import json

import placement

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QLineEdit, QFileDialog, QComboBox, QMessageBox, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import (QIcon, QPixmap)


class MP4CreatorThread(QThread):
    creationStarted = Signal()
    progressUpdated = Signal(int, str)
    creationFinished = Signal()

    def __init__(self, image_directory, audio_file, slideshow_path):
        super().__init__()
        self.image_directory = image_directory
        self.audio_file = audio_file
        self.slideshow_path = slideshow_path

    def run(self):
        self.creationStarted.emit()
        placement.create_slideshow(self.image_directory, self.audio_file, self.slideshow_path, self.update_progress)
        self.creationFinished.emit()

    def update_progress(self, value, label=None):
        self.progressUpdated.emit(value, label)


class SlideshowCreator(QWidget):
    def __init__(self):
        super().__init__()
        settings = self.load_settings()
        self.current_language = self.get_language(settings)
        self.translations = self.load_translations(self.current_language)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.locale_subjects = dict()
        self.direction_subjects = list()
        self.setup_ui()
        self.apply_settings(settings)
        self.change_language(self.current_language)

    @staticmethod
    def get_settings_file():
        home_dir = os.path.expanduser('~')
        filename = 'SlideshowMaker.json'
        return os.path.join(home_dir, filename)

    def save_settings(self, language, imageDirectory='', audioFile='', outputPath=''):
        settings = {
            'language': language,
            'imageDirectory': imageDirectory,
            'audioFile': audioFile,
            'outputPath': outputPath,
        }
        try:
            with open(self.get_settings_file(), 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            QMessageBox.warning(self, self.translate_key('saving_settings_warning'), str(e))

    def load_settings(self):
        settings = {
            'language': 'English',
            'imageDirectory': os.path.expanduser("~"),
            'audioFile': '',
            'outputPath': '',
        }
        try:
            with open(self.get_settings_file(), 'r') as f:
                settings.update(json.load(f))
        except FileNotFoundError:
            pass
        return settings

    def apply_settings(self, settings):
        self.langComboBox.setCurrentText(self.current_language)
        self.dirImagesLineEdit.setText(settings.get('imageDirectory', ''))
        self.audioFileLineEdit.setText(settings.get('audioFile', ''))
        self.outputFileLineEdit.setText(settings.get('outputPath', ''))

    @staticmethod
    def get_language(settings):
        return settings.get('language', 'English')

    @staticmethod
    def load_language_codes():
        path = 'locales/language_codes.json'
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @classmethod
    def load_language_names(cls):
        language_codes = cls.load_language_codes()
        return list(language_codes.keys())

    @classmethod
    def load_translations(cls, language_name):
        language_codes = cls.load_language_codes()
        language_code = language_codes.get(language_name, "en")
        path = f'locales/{language_code}.json'
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def translate_key(self, text_key):
        return self.translations.get(text_key, text_key)


    def setup_ui(self):
        # Update Logo
        self.logoLabel = QLabel(self)
        self.logoPixmap = QPixmap('images/logo.png')
        scaledLogoPixmap = self.logoPixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logoLabel.setPixmap(scaledLogoPixmap)
        self.logoLabel.setFixedSize(scaledLogoPixmap.size())
        self.layout.addWidget(self.logoLabel)

        # Language selection
        self.languageLabel = QLabel()
        self.locale_subjects['language_label'] = self.languageLabel
        self.langComboBox = QComboBox()
        self.langComboBox.addItems(self.load_language_names())
        self.langComboBox.currentTextChanged.connect(self.change_language)
        langLayout = QHBoxLayout()
        langLayout.addWidget(self.languageLabel)
        langLayout.addWidget(self.langComboBox)
        self.direction_subjects.append(langLayout)
        self.layout.addLayout(langLayout)

        # Image directory selection
        self.dirImagesLabel = QLabel()
        self.locale_subjects['images_directory_label'] = self.dirImagesLabel
        self.dirImagesLineEdit = QLineEdit()
        self.dirImagesButton = QPushButton()
        self.dirImagesButton.clicked.connect(self.choose_input_images)
        self.locale_subjects['choose_directory'] = self.dirImagesButton
        dirImagesLayout = QHBoxLayout()
        dirImagesLayout.addWidget(self.dirImagesLabel)
        dirImagesLayout.addWidget(self.dirImagesLineEdit)
        dirImagesLayout.addWidget(self.dirImagesButton)
        self.direction_subjects.append(dirImagesLayout)
        self.layout.addLayout(dirImagesLayout)

        # Audio file selection
        self.audioFileLabel = QLabel()
        self.locale_subjects['audio_mp3_label'] = self.audioFileLabel
        self.audioFileLineEdit = QLineEdit()
        self.audioFileButton = QPushButton()
        self.audioFileButton.clicked.connect(self.choose_input_audio)
        self.locale_subjects['choose_mp3_button'] = self.audioFileButton
        audioFileLayout = QHBoxLayout()
        audioFileLayout.addWidget(self.audioFileLabel)
        audioFileLayout.addWidget(self.audioFileLineEdit)
        audioFileLayout.addWidget(self.audioFileButton)
        self.direction_subjects.append(audioFileLayout)
        self.layout.addLayout(audioFileLayout)


        # Output file selection
        self.outputFileLabel = QLabel()
        self.locale_subjects['output_mp4_label'] = self.outputFileLabel
        self.outputFileLineEdit = QLineEdit()
        self.outputFileButton = QPushButton()
        self.outputFileButton.clicked.connect(self.create_output_video)
        self.locale_subjects['create_mp4_button'] = self.outputFileButton
        outputFileLayout = QHBoxLayout()
        outputFileLayout.addWidget(self.outputFileLabel)
        outputFileLayout.addWidget(self.outputFileLineEdit)
        outputFileLayout.addWidget(self.outputFileButton)
        self.direction_subjects.append(outputFileLayout)
        self.layout.addLayout(outputFileLayout)

        # Process button
        self.processButton = QPushButton(self.translate_key('process_button'))
        self.locale_subjects['process_button'] = self.processButton
        self.processButton.clicked.connect(self.create_slideshow)
        self.layout.addWidget(self.processButton)

        # Progress Bar
        self.progressLabel = QLabel('')
        self.progressStatus = ''
        self.layout.addWidget(self.progressLabel)
        self.progressBar = QProgressBar(self)
        self.progressBar.setValue(0)  # start value
        self.progressBar.setMaximum(100)  # 100% completion
        self.layout.addWidget(self.progressBar)

    def reset_progress(self):
        self.set_progress_status('')
        self.progressBar.setValue(0)

    def choose_input_images(self):
        self.choose_directory(self.dirImagesLineEdit)

    def choose_directory(self, parent):
        dir_path = QFileDialog.getExistingDirectory(self,
                                                   self.translate_key('choose_directory'),
                                                   dir=parent.text())
        if dir_path:
            self.dirImagesLineEdit.setText(dir_path)

        self.reset_progress()

    def choose_input_audio(self):
        self.choose_audio_file(self.audioFileLineEdit)

    def create_output_video(self):
        self.create_video_file(self.outputFileLineEdit)

    def choose_audio_file(self, parent):
        self.choose_file(parent, 'Audio files (*.mp3)')

    def create_video_file(self, parent):
        self.create_file(parent, 'Video files (*.mp4)')

    def choose_file(self, parent, format_filter):
        file_path, _ = QFileDialog.getOpenFileName(self,
                                                   self.translate_key('choose_file'),
                                                   dir=parent.text(),
                                                   filter=format_filter)
        if file_path:
            parent.setText(file_path)
        self.reset_progress()

    def create_file(self, parent, format_filter):
        file_path, _ = QFileDialog.getSaveFileName(self,
                                                   self.translate_key('create_file'),
                                                   dir=parent.text(),
                                                   filter=format_filter)
        if file_path:
            parent.setText(file_path)
        self.reset_progress()

    def change_language(self, language):
        self.current_language = language
        self.translations = self.load_translations(language)

        # Update texts
        self.setWindowTitle(self.translate_key('title'))

        if self.progressStatus:
            self.progressLabel.setText(self.translate_key(self.progressStatus))

        for locale_key in self.locale_subjects:
            self.locale_subjects[locale_key].setText(self.translate_key(locale_key))

        # Update layout
        is_rtl = (language == 'עברית')
        for direction_subject in self.direction_subjects:
            direction_subject.setDirection(QHBoxLayout.RightToLeft if is_rtl else QHBoxLayout.LeftToRight)

    def create_slideshow(self):
        if not os.path.isdir(self.dirImagesLineEdit.text()):
            QMessageBox.warning(self, self.translate_key('error_title'), self.translate_key('directory_not_found'))
            return

        images = [
            filename for
            filename in os.listdir(self.dirImagesLineEdit.text()) if
            filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp'))
        ]
        images_count = len(images)

        if not images_count:
            QMessageBox.warning(self, self.translate_key('error_title'), self.translate_key('no_images_found'))
            return

        if images_count > 50:
            QMessageBox.warning(self, self.translate_key('error_title'), self.translate_key('max_images_exceed'))
            return

        if not os.path.isfile(self.audioFileLineEdit.text()) or not self.audioFileLineEdit.text().endswith('mp3'):
            QMessageBox.warning(self, self.translate_key('error_title'), self.translate_key('audio_not_found'))
            return

        if not self.outputFileLineEdit.text() or not self.outputFileLineEdit.text().endswith('mp4'):
            QMessageBox.warning(self, self.translate_key('error_title'), self.translate_key('output_path_not_found'))
            return

        image_directory = self.dirImagesLineEdit.text()
        audio_file = self.audioFileLineEdit.text()
        slideshow_path = self.outputFileLineEdit.text()

        try:
            self.mp4Thread = MP4CreatorThread(image_directory, audio_file, slideshow_path)
            self.mp4Thread.creationStarted.connect(self.on_pdf_creation_started)
            self.mp4Thread.progressUpdated.connect(self.update_progress_bar)
            self.mp4Thread.creationFinished.connect(self.on_pdf_creation_finished)
            self.mp4Thread.start()
        except Exception as e:
            error_message = f"{self.translate_key('video_creation_failed')} {str(e)}"
            QMessageBox.warning(self, self.translate_key('error_title'), error_message)

    def on_pdf_creation_started(self):
        self.processButton.setEnabled(False)
        self.save_settings(self.current_language,
                           self.dirImagesLineEdit.text(), self.audioFileLineEdit.text(),
                           self.outputFileLineEdit.text())
        self.set_progress_status('creation')

    def set_progress_status(self, status):
        self.progressStatus = status
        self.progressLabel.setText(self.translate_key(self.progressStatus))

    def update_progress_bar(self, value, label):
        if label:
            self.set_progress_status(label)
        self.progressBar.setValue(value)

    def on_pdf_creation_finished(self):
        self.set_progress_status('finished')
        self.processButton.setEnabled(True)
        QMessageBox.information(self, self.translate_key('success_title'), self.translate_key('success_message'))

if __name__ == '__main__':
    if hasattr(sys, '_MEIPASS'):
        os.chdir(sys._MEIPASS)
    app = QApplication(sys.argv)
    window = SlideshowCreator()
    window.show()
    sys.exit(app.exec())
