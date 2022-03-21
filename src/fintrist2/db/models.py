"""
The engine that applies analyses to data and generates alerts.
"""
import logging
import pickle
import arrow

import pandas as pd
from mongoengine.document import Document, EmbeddedDocument
from mongoengine.fields import (
    DateTimeField, DictField, EmbeddedDocumentField,
    EmbeddedDocumentListField, IntField, FileField,
    ListField, MapField, ReferenceField, StringField,
    BooleanField, BinaryField, GridFSProxy,
)
from mongoengine.errors import SaveConditionError, DoesNotExist
from pymongo.errors import InvalidDocument
from mongoengine import signals
from bson.dbref import DBRef

from fintrist2 import Config

__all__ = ('clean_files', 'Study')

logger = logging.getLogger(__name__)

def handler(event):
    """Signal decorator to allow use of callback functions as class decorators."""

    def decorator(fn):
        def apply(cls):
            event.connect(fn, sender=cls)
            return cls

        fn.apply = apply
        return fn

    return decorator

@handler(signals.pre_delete)
def clean_files(sender, document):  #pylint: disable=unused-argument
    """Signal deleted Studies to remove data files."""
    document.remove_files()

@clean_files.apply
class Study(Document):
    """Contains data process results.

    Can act as a generic data archive.
    """
    # ID
    name = StringField(max_length=120, required=True, unique=True)

    # Data Inputs
    params = DictField()  # Processing parameters.

    # Data Outputs
    newfile = MapField(FileField())
    fileversions = MapField(FileField())
    versiondefault = StringField(default='default')
    _timestamp = StringField()

    # Meta
    notes = MapField(ListField(StringField()))
    schema_version = IntField(default=1)
    meta = {
        'strict': False,
        'abstract': True,
        'allow_inheritance': True,
        }

    def __repr__(self):
        return f"Study: {self.name}"

    # pylint: disable=no-member
    def clean(self):
        """Clean attributes."""
        # Timestamp display
        try:
            self._timestamp = self.timestamp.format()
        except AttributeError:
            self._timestamp = None
        # Subclassed cleaning
        self.subclean()

    def subclean(self):
        """Cleaning operations for subclasses."""
        pass

    ## Methods defining the Study ##

    def rename(self, newname):
        """Rename the Study."""
        self.name = newname
        self.save()

    @property
    def db_obj(self):
        """Get the database object."""
        cls = self.__class__
        try:
            return cls.objects(name=self.name).get()
        except DoesNotExist:
            return self

    ## Methods related to scheduling runs ##

    @property
    def timestamp(self):
        """Preprocess the timestamp to ensure consistency."""
        return self.get_timestamp(self.versiondefault)

    def get_timestamp(self, version):
        try:
            recent_file = self.fileversions.get(version)
            return arrow.get(recent_file.uploadDate).to(Config.TZ)
        except:
            return

    ## Methods for handling inputs ##

    def add_params(self, newparams):
        """Add all of the params in the given dict."""
        self.params.update(newparams)
        self.save()

    def remove_inputs(self, inputs):
        """Remove all of the inputs in the given iterable of names."""
        for key in inputs:
            self.params.pop(key, None)
        self.save()

    ## Methods for handling the saved data ##

    @property
    def version(self):
        return getattr(self, '_version', self.versiondefault)

    @version.setter
    def version(self, label):
        self._version = label

    @property
    def all_versions(self):
        return list(self.fileversions.keys())

    @property
    def data(self):
        """Preprocess the data field to return the data in a usable format."""
        if self.newfile.get(self.version):
            self.transfer_file(self.newfile, self.fileversions)
        try:
            file_obj = self.fileversions.get(self.version).get()
            result = file_obj.read()
            file_obj.seek(0)
            return pickle.loads(result)
        except:
            return None

    @data.setter
    def data(self, newdata):
        """Process the data for storage."""
        if newdata is None:
            self.remove_files()
        else:
            self.write_version(self.newfile, newdata)
            self.transfer_file(self.newfile, self.fileversions)

    def write_to(self, field, newdata):
        """Write data to a FileField."""
        field.new_file()
        field.write(pickle.dumps(newdata))
        field.close()
        self.save()

    def write_version(self, field, newdata):
        """Write data into a mapped FileField."""
        fileslot = self.get_fileslot(field)
        self.write_to(fileslot, newdata)

    def get_fileslot(self, field):
        """Get an existing fileslot in a mapfield, or create it."""
        fileslot = field.get(self.version, GridFSProxy())
        field[self.version] = fileslot
        return fileslot

    def copy_file(self, filesrc, filedest):
        """Copy the data from filesrc to filedest."""
        newfile = filesrc.read()
        filedest.replace(newfile)
        self.save()

    def transfer_file(self, filesrc, filedest):
        """Transfer a file between FileFields, possibly within a MapField."""
        try:
            filesrc = filesrc.pop(self.version, None)
        except AttributeError:
            pass
        if isinstance(filedest, dict):
            filedest = self.get_fileslot(filedest)
        self.copy_file(filesrc, filedest)
        filesrc.delete()
        self.save()

    def remove_file(self, field):
        """Remove a file version from a MapField."""
        field[self.version].delete()
        del field[self.version]
        self.save()

    def remove_files(self):
        """Remove the data."""
        for field in (self.fileversions, self.newfile):
            try:
                self.remove_file(field)
            except KeyError:
                pass

    def rename_data(self, oldname, newname):
        """Rename the data file."""
        try:
            self.fileversions[newname].delete()
        except KeyError:
            pass
        self.fileversions[newname] = self.fileversions[oldname]
        del self.fileversions[oldname]
        self.save()

    def add_note(self, title='default', text=None):
        """Add a note to the notes field."""
        entry = self.notes.get(title, [])
        if text:
            entry.append(text)
        self.notes[title] = entry
        self.save()

    def del_note(self, title='default', index=None):
        """Delete the specified note."""
        if index is None:
            self.notes.pop(title, None)
        else:
            entry = self.notes.get(title, [])
            entry.pop(index)
        self.save()

    def read_notes(self, title=None):
        """Read the notes."""
        if title is None:
            for key in reversed(self.notes.keys()):
                self.read_notes(key)
        else:
            entry = [f"{i}: {note}" for i, note in enumerate(self.notes.get(title, []))]
            print(f"{title}\n\t" + "\n\t".join(entry))

@clean_files.apply
class StockData(Study):
    """Stock data."""

    meta = {
        'collection': 'stocks',
        }

    def __repr__(self):
        return f"StockData: {self.name}"
