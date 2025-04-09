from talelle_setup import Path, TALELLE_DIR, config_log
TALELLE_TOOL = Path(__file__).stem
config_log(TALELLE_TOOL)

import sys
import os
import subprocess
import json

import placement
import logging

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QLineEdit, QFileDialog, QComboBox, QMessageBox, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap

logger = logging.getLogger(__name__)
logger.info(f'{TALELLE_TOOL} started')


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
        self.project_path, self.project_folder = self.get_project_path(settings)
        self.images_folder = self.get_images_folder(settings)

        # declare QComponent groups
        self.locale_subjects = dict()
        self.direction_subjects = list()

        # declare QComponents
        self.langComboBox = None
        self.projLabel = None
        self.projLineEdit = None
        self.dirImagesLineEdit = None
        self.audioFileLineEdit = None
        self.outputFileLineEdit = None
        self.processButton = None
        self.progressStatus = None
        self.progressBar = None


        self.setup_ui()
        self.apply_settings(settings)
        self.change_language(self.current_language)

    @staticmethod
    def get_settings_file():
        return os.path.join(TALELLE_DIR, f'{TALELLE_TOOL}.json')

    def save_settings(self, language):
        settings = {
            'language': language,
            'projectPath': self.project_path,
            'projectFolder': self.project_folder,
            'imagesFolder': self.images_folder,
        }
        try:
            with open(self.get_settings_file(), 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            QMessageBox.warning(self, self.translate_key('saving_settings_warning'), str(e))

    def load_settings(self):
        settings = {
            'language': 'English',
        }
        try:
            with open(self.get_settings_file(), 'r') as f:
                settings.update(json.load(f))
        except FileNotFoundError:
            pass
        return settings

    @staticmethod
    def get_project_path(settings) -> tuple[str, str]:
        return \
            settings.get('projectPath', os.path.expanduser("~")), \
                settings.get('projectFolder', 'projects')

    @staticmethod
    def get_images_folder(settings) -> str:
        return settings.get('imagesFolder', 'images')

    def apply_settings(self, settings):
        self.langComboBox.setCurrentText(self.current_language)

        date_project_path = os.path.join(self.project_path, self.project_folder)
        self.projLineEdit.setText(date_project_path)

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
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Update Logo
        logoLabel = QLabel(self)
        self.logoPixmap = QPixmap('images/logo.png')
        scaledLogoPixmap = self.logoPixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation)
        logoLabel.setPixmap(scaledLogoPixmap)
        logoLabel.setFixedSize(scaledLogoPixmap.size())
        layout.addWidget(logoLabel)

        # Language selection
        languageLabel = QLabel()
        langComboBox = QComboBox()
        langComboBox.addItems(self.load_language_names())
        langComboBox.currentTextChanged.connect(self.change_language)
        langLayout = QHBoxLayout()
        langLayout.addWidget(languageLabel)
        langLayout.addWidget(langComboBox)
        layout.addLayout(langLayout)

        # Project selection
        projLabel = QLabel()
        projLineEdit = QLineEdit()
        projButton = QPushButton()

        projButton.clicked.connect(self.choose_project)
        projLayout = QHBoxLayout()
        projLayout.addWidget(projLabel)
        projLayout.addWidget(projLineEdit)
        projLayout.addWidget(projButton)
        layout.addLayout(projLayout)

        # Image directory selection
        dirImagesLabel = QLabel()
        dirImagesLineEdit = QLineEdit()
        dirImagesLineEdit.setMinimumWidth(400)
        dirImagesButton = QPushButton()
        dirImagesButton.clicked.connect(self.choose_input_images)
        dirImagesLayout = QHBoxLayout()
        dirImagesLayout.addWidget(dirImagesLabel)
        dirImagesLayout.addWidget(dirImagesLineEdit)
        dirImagesLayout.addWidget(dirImagesButton)
        layout.addLayout(dirImagesLayout)

        # Audio file selection
        audioFileLabel = QLabel()
        audioFileLineEdit = QLineEdit()
        audioFileButton = QPushButton()
        audioFileButton.clicked.connect(self.choose_input_audio)
        audioFileLayout = QHBoxLayout()
        audioFileLayout.addWidget(audioFileLabel)
        audioFileLayout.addWidget(audioFileLineEdit)
        audioFileLayout.addWidget(audioFileButton)
        layout.addLayout(audioFileLayout)


        # Output file selection
        outputFileLabel = QLabel()
        outputFileLineEdit = QLineEdit()
        outputFileButton = QPushButton()
        outputFileButton.clicked.connect(self.create_output_video)
        outputFileLayout = QHBoxLayout()
        outputFileLayout.addWidget(outputFileLabel)
        outputFileLayout.addWidget(outputFileLineEdit)
        outputFileLayout.addWidget(outputFileButton)
        layout.addLayout(outputFileLayout)

        # Process button
        processButton = QPushButton(self.translate_key('process_button'))
        processButton.clicked.connect(self.create_slideshow)
        layout.addWidget(processButton)

        # Progress Bar
        progressLabel = QLabel('')
        progressStatus = ''
        layout.addWidget(progressLabel)
        progressBar = QProgressBar(self)
        progressBar.setValue(0)  # start value
        progressBar.setMaximum(100)  # 100% completion
        layout.addWidget(progressBar)

        self.locale_subjects['language_label'] = languageLabel
        self.locale_subjects['project_label'] = projLabel
        self.locale_subjects['choose_project'] = projButton
        self.locale_subjects['images_directory_label'] = dirImagesLabel
        self.locale_subjects['choose_directory'] = dirImagesButton
        self.locale_subjects['audio_mp3_label'] = audioFileLabel
        self.locale_subjects['choose_mp3_button'] = audioFileButton
        self.locale_subjects['output_mp4_label'] = outputFileLabel
        self.locale_subjects['create_mp4_button'] = outputFileButton
        self.locale_subjects['process_button'] = processButton

        self.direction_subjects.append(langLayout)
        self.direction_subjects.append(projLayout)
        self.direction_subjects.append(dirImagesLayout)
        self.direction_subjects.append(audioFileLayout)
        self.direction_subjects.append(outputFileLayout)

        self.langComboBox = langComboBox
        self.projLabel = projLabel
        self.projLineEdit = projLineEdit
        self.dirImagesLineEdit = dirImagesLineEdit
        self.audioFileLineEdit = audioFileLineEdit
        self.outputFileLineEdit = outputFileLineEdit
        self.processButton = processButton
        self.progressLabel = progressLabel
        self.progressStatus = progressStatus
        self.progressBar = progressBar





    def reset_progress(self):
        self.set_progress_status('')
        self.progressBar.setValue(0)

    def choose_project(self):
        proj_path = QFileDialog.getExistingDirectory(self,
                                                     self.translate_key('choose_project'),
                                                     dir=self.projLineEdit.text())
        if proj_path:
            proj_path = os.path.normpath(proj_path)
            self.projLineEdit.setText(proj_path)

            images_path = os.path.join(proj_path, self.images_folder)
            self.dirImagesLineEdit.setText(images_path)

            proj_name = os.path.basename(proj_path)
            proj_parent_name = os.path.basename(os.path.dirname(proj_path))
            file_name = f'{proj_parent_name}_{proj_name}'
            file_path = os.path.join(proj_path, file_name)
            self.audioFileLineEdit.setText(f'{file_path}.mp3')
            self.outputFileLineEdit.setText(f'{file_path}.mp4')

        self.reset_progress()

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
            direction_subject.setDirection(QHBoxLayout.Direction.RightToLeft if is_rtl else QHBoxLayout.Direction.LeftToRight)

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
            self.mp4Thread.creationStarted.connect(self.on_slideshow_creation_started)
            self.mp4Thread.progressUpdated.connect(self.update_progress_bar)
            self.mp4Thread.creationFinished.connect(self.on_slideshow_creation_finished)
            self.mp4Thread.start()
        except Exception as e:
            error_message = f"{self.translate_key('video_creation_failed')} {str(e)}"
            QMessageBox.warning(self, self.translate_key('error_title'), error_message)

    def on_slideshow_creation_started(self):
        self.processButton.setEnabled(False)
        self.save_settings(self.current_language)
        self.set_progress_status('creation')

    def set_progress_status(self, status):
        self.progressStatus = status
        self.progressLabel.setText(self.translate_key(self.progressStatus))

    def update_progress_bar(self, value, label):
        if label:
            self.set_progress_status(label)
        self.progressBar.setValue(value)

    def on_slideshow_creation_finished(self):
        self.set_progress_status('finished')
        self.processButton.setEnabled(True)
        QMessageBox.information(self, self.translate_key('success_title'), self.translate_key('success_message'),
                                QMessageBox.StandardButton.Ok)

if __name__ == '__main__':
    if hasattr(sys, '_MEIPASS'):
        os.chdir(sys._MEIPASS)

        if os.name == 'nt':
            print('WINDOWS, monkey patching subprocess to be silent')
            original_popen = subprocess.Popen
            def silent_popen_windows(*args, **kwargs):
                return original_popen(*args, **kwargs, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.Popen = silent_popen_windows

    app = QApplication(sys.argv)
    window = SlideshowCreator()
    window.show()
    sys.exit(app.exec())
