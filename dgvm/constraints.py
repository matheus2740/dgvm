from collections import deque


class ConstraintViolation(Exception):
    pass


class Constraint(object):

    def __init__(self, name, func, target, related):
        from .datamodel.meta import VMAttribute
        related = related or tuple()
        if not isinstance(target, VMAttribute):
            raise TypeError('Target for constraint must be of type VMAttribute, not ' + str(type(target)))

        for target in related:
            if not isinstance(target, VMAttribute):
                raise TypeError('Related objects for constraint must be of type VMAttribute, not ' + str(type(target)))

        self.name = name
        self.func = func
        self._target = target
        self._related = related

    def related(self, model_instance):
        return {related.name: related._get_wrapped_value(model_instance) for related in self._related}

    def target(self, model_instance):
        return self._target._get_wrapped_value(model_instance)

    def validate(self, model_instance, *args, **kwargs):
        return False

    def __str__(self):
        return '<%s: %s on %s>' % (type(self).__name__, self.name, self._target.name)


class AttributeChangedConstraint(Constraint):

    def __init__(self, name, func, target, related):
        super(AttributeChangedConstraint, self).__init__(name, func, target, related)

    def validate(self, model_instance, new):
        return self.func(self, self.target(model_instance), new, self.related(model_instance))


class ConstraintCollection(object):

    def __init__(self, constraints=None):
        self.constraints = constraints or deque()

    def add_constraint(self, cons):
        self.constraints.append(cons)

    def validate(self, instance, value):
        for constraint in self.constraints:
            validates = constraint.validate(instance, value)
            if not validates:
                raise ConstraintViolation(str(constraint))

    def __iter__(self):
        return iter(self.constraints)


class constraint(object):
    """
        Decorators
    """
    class on_change(object):
        def __init__(self, target, related=tuple()):
            self.func = None
            self.target = target
            self.related = related

        def __call__(self, func):
            self.func = func
            c = AttributeChangedConstraint(func.__name__, func, self.target, self.related)
            self.target.on_change.add_constraint(c)
            return c

    # TODO: more constraints: on_create, on_destroy


# TODO: create an event system. this must be tought carefully as to avoid side-effects and non-determinism

