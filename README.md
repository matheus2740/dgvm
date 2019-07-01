# dgvm
dynamic game virtual machine kit


DGVM is a study into python's advanced features such as metaprogramming,
with the goal of being a "virtual machine kit", i.e. a way for the user to define transactional state
as a virtual machine with instructions and data models.

General goals of the project:

* Allow user to define data models (similar to ORM)
* Allow user to define custom instructions
* Allow state to be serialized and deserialized (with full execution history)
* Allow individual commits/diffs to be serialized and deserialized
* Allow for network conectivity and automatic state syncing


Non-goals:

* Optimal performance


##### Documentation is currently a work in progress as this project is a result of a couple of sprints focused on getting a minimal use case working. Please see the test cases to have some insight on the use cases. 


TODO:
* Change ipc approach from threading to event loop
* docs docs docs
* more tests
* Fully functional use case sample
