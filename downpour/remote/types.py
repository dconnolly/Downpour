from twisted.protocols import amp

class Dict(amp.Argument):

    def __init__(self, subargs):
        self.subargs = subargs

    def fromStringProto(self, inString, proto):
        boxes = amp.parseString(inString)
        return amp._stringsToObjects(boxes[0], self.subargs, proto)

    def toStringProto(self, inObject, proto):
        return amp._objectsToStrings(inObject, self.subargs, amp.Box(), proto).serialize()
