# coding: utf-8
__author__ = 'salvia'

from threading import Lock

from .meta import DatamodelMeta, DatamodelStates
from ..builtin_instructions import InstantiateModel, DestroyInstance


required_methods = {}


class InvalidModel(Exception):
    pass


# TODO: implement .objects(.all/.filter)
class Datamodel(metaclass=DatamodelMeta):
    """
        Base class for all models.

    """

    _state = DatamodelStates.NORMAL

    _lock = Lock()

    def __init__(self, vm, noinit=False, **kwargs):
        from dgvm.datamodel import ForeignModel
        from dgvm.datamodel import ntuple

        self.vm = vm

        self._state = DatamodelStates.NORMAL

        if noinit:
            return

        # set the model state to ENGINE_CHANGING, which permits attribute setting without checks and constraints
        self._state = DatamodelStates.ENGINE_CHANGING

        # id is a special snowflake and need separate attention.
        id = self._next_id(vm)
        self._vmattrs['_id']._set_wrapped_value(self, id, id)
        self.id = id

        # for each attribute of this model
        for k, v in self._vmattrs.items():

            # id is a special snowflake and need separate attention. which he got. above.
            if k == '_id':
                continue

            # value is passed in ctor, just go ahead
            if k in kwargs and kwargs[k] is not None:
                setattr(self, k, kwargs[k])
            elif isinstance(v, ForeignModel) and k + '_id' in kwargs:
                setattr(self, k, v.subtype.get_by_id(self.vm, kwargs[k + '_id']))
            # no value provided in ctor, do we require it?
            else:
                # nope, we don't require it, just leave it as None
                if v.null:
                    setattr(self, k, None)
                # yes we require it, do we have a default value?
                else:
                    # yes we have a default value, use it
                    if v.default:
                        setattr(self, k, v.default)
                    # no we don't have a default value and something is required, so raise and let user fix it.
                    else:
                        self._state = DatamodelStates.NORMAL
                        raise ValueError('Cannot instantiate %s: value for %s is required.' % (type(self).__name__, k,))

        # set the model state to NORMAL, which forbids attribute changes.
        self._state = DatamodelStates.NORMAL

        # emit an InstantiateModel instruction to the vm
        self.vm.execute([self.__instantiate_instruction()])

    def is_destroyed(self):
        return self._state == DatamodelStates.DESTROYED

    def destroy(self):
        self.vm.execute([self.__destroy_instruction()])
        self._state = DatamodelStates.DESTROYED

    def __destroy_instruction(self):
        return DestroyInstance(self.__class__, self.id)

    def __instantiate_instruction(self):
        return InstantiateModel(self.__class__, self._attrs)

    def _to_user_changing_state(self):
        self._state = DatamodelStates.USER_CHANGING

    def _to_normal_state(self):
        self._state = DatamodelStates.NORMAL

    def data_dict(self, unwrap=False):

        d = {
            'class': type(self).__name__,
            'attributes': []
        }

        for name, attr in self._vmattrs.items():
            if name == '_id':
                d['attributes'].append({
                    'class': type(attr).__name__,
                    'name': 'id',
                    'value': self.id
                })
                continue
            val = attr._get_wrapped_value(self)
            if unwrap:
                d['attributes'].append({
                    'class': type(attr).__name__,
                    'name': attr.name,
                    'value': val.data_dict(True) if isinstance(val, Datamodel) else val
                })
            else:
                d['attributes'].append({
                    'class': type(val).__name__ if isinstance(val, Datamodel) else type(attr).__name__,
                    'name': attr.name + '_id' if isinstance(val, Datamodel) else attr.name,
                    'value': val.id if isinstance(val, Datamodel) else val
                })
        return d

    @property
    def _attrs(self):
        from dgvm.datamodel import ntuple

        def make_serializeable(a):
            if isinstance(a, (tuple, ntuple)):
                return list(a)
            return a

        return {a['name']: make_serializeable(a['value']) for a in self.data_dict()['attributes']}

    @classmethod
    def _next_id(cls, vm):
        key = cls.__name__ + '/IDCOUNTER'
        val = None

        with cls._lock:
            current_id = vm.heap.get(key) or 0
            val = current_id + 1
            vm.heap.set(key, val)

        return val

    @classmethod
    def get_by_id(cls, vm, id):

        item = cls(vm, noinit=True)
        item._state = DatamodelStates.ENGINE_CHANGING
        item.id = id
        item._state = DatamodelStates.NORMAL
        return item



