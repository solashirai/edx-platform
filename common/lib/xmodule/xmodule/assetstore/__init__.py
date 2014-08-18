

from opaque_keys.edx.keys import CourseKey, AssetKey


class AssetMetadata(object):
    """
    Stores the metadata associated with a particular course asset. The asset metadata gets stored
    in the modulestore.
    """

    TOP_LEVEL_ATTRS = ['basename', 'internal_name', 'locked']
    EDIT_INFO_ATTRS = ['curr_version', 'prev_version', 'edited_by', 'edited_on']
    ALLOWED_ATTRS = TOP_LEVEL_ATTRS + EDIT_INFO_ATTRS

    def __init__(self, asset_id,
                 basename=None, internal_name=None, locked=None,
                 curr_version=None, prev_version=None,
                 edited_by=None, edited_on=None, **kwargs):
        """
        Construct a AssetMetadata object.

        Arguments:
            asset_id (AssetKey): Key identifying this particular asset.
            basename (str): Original path to file at asset upload time.
            internal_name (str): Name under which the file is stored internally.
            locked (bool): If True, only course participants can access the asset.
            curr_version (str): Current version of the asset.
            prev_version (str): Previous version of the asset.
            edited_by (str): Username of last user to upload this asset.
            edited_on (datetime): Datetime of last upload of this asset.
        """
        self.asset_id = asset_id
        self.basename = basename  # Path w/o filename.
        self.internal_name = internal_name
        self.locked = locked
        self.curr_version = curr_version
        self.prev_version = prev_version
        self.edited_by = edited_by
        self.edited_on = edited_on

    def __eq__(self, other):
        return self.asset_id == other.asset_id

    def __repr__(self):
        return """AssetMetadata('{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}')"""\
                .format(self.asset_id,
                        self.basename, self.internal_name, self.locked,
                        self.curr_version, self.prev_version,
                        self.edited_by, self.edited_on)

    def set_attrs(self, attr_dict):
        """
        Set the attributes on the metadata. Ignore all those outside the known fields.

        Arguments:
            attr_dict: Prop, val dictionary of all attributes to set.
        """
        for attr, val in attr_dict.iteritems():
            if attr in self.ALLOWED_ATTRS:
                setattr(self, attr, val)

    def to_mongo(self):
        """
        Converts metadata properties into a MongoDB-storable dict.
        """
        return {
           'filename': self.asset_id.path,
           'basename': self.basename,
           'internal_name': self.internal_name,
           'locked': self.locked,
           'edit_info': {
              'curr_version': self.curr_version,
              'prev_version': self.prev_version,
              'edited_by': self.edited_by,
              'edited_on': self.edited_on
              }
           }

    def from_mongo(self, asset_doc):
        """
        Fill in all metadata fields from a MongoDB document.

        The asset_id and upload_name props are initialized upon construction only.
        """
        if asset_doc is None:
            return
        assert isinstance(asset_doc, dict)
        self.basename = asset_doc['basename']
        self.internal_name = asset_doc['internal_name']
        self.locked = asset_doc['locked']
        edit_info = asset_doc['edit_info']
        self.curr_version = edit_info['curr_version']
        self.prev_version = edit_info['prev_version']
        self.edited_by = edit_info['edited_by']
        self.edited_on = edit_info['edited_on']


