"use strict";

var QWebChannel = function(transport, initCallback) {
    if (typeof transport !== "object" || typeof transport.send !== "function") {
        console.error("The QWebChannel transport object must be an object with a send function.");
        return;
    }

    var channel = this;
    this.transport = transport;
    this.send = function(data) {
        channel.transport.send(JSON.stringify(data));
    };

    this.transport.onmessage = function(message) {
        var data = typeof message.data === "string" ? JSON.parse(message.data) : message.data;
        switch (data.type) {
            case 1: // signal
                channel.handleSignal(data);
                break;
            case 2: // response
                channel.handleResponse(data);
                break;
            case 3: // init
                channel.handleInit(data);
                break;
        }
    };

    this.execCallbacks = {};
    this.execId = 0;
    this.objects = {};

    this.handleInit = function(data) {
        for (var objectName in data.objects) {
            var object = new QObject(objectName, data.objects[objectName], channel);
            channel.objects[objectName] = object;
        }

        for (var objectName in data.objects) {
            var object = channel.objects[objectName];
            for (var i = 0; i < object.__id__.length; ++i) {
                var signalName = object.__id__[i];
                object[signalName].connect();
            }
        }

        if (initCallback) {
            initCallback(channel);
        }
    };

    this.handleResponse = function(data) {
        if (!data.id) return;
        var callback = channel.execCallbacks[data.id];
        if (callback) {
            delete channel.execCallbacks[data.id];
            callback(data.data);
        }
    };

    this.handleSignal = function(data) {
        var object = channel.objects[data.object];
        if (object) {
            object.signalEmitted(data.signal, data.args);
        }
    };

    this.send({ type: 1 }); // signal initialization
};

function QObject(name, data, webChannel) {
    this.__id__ = name;
    this.__webChannel__ = webChannel;

    var object = this;

    // Methods
    data.methods.forEach(function(method) {
        var methodName = method[0];
        var methodId = method[1];
        object[methodName] = function() {
            var args = Array.prototype.slice.call(arguments);
            var callback;
            if (args.length > 0 && typeof args[args.length - 1] === "function") {
                callback = args.pop();
            }

            var id = ++webChannel.execId;
            if (callback) {
                webChannel.execCallbacks[id] = callback;
            }

            webChannel.send({
                type: 2, // method call
                object: name,
                method: methodId,
                args: args,
                id: id
            });
        };
    });

    // Signals
    this.__id__ = [];
    data.signals.forEach(function(signal) {
        var signalName = signal[0];
        var signalId = signal[1];
        object.__id__.push(signalName);
        object[signalName] = {
            connect: function(callback) {
                if (typeof callback !== "function") return;
                if (!object[signalName].slots) {
                    object[signalName].slots = [];
                }
                object[signalName].slots.push(callback);
            },
            disconnect: function(callback) {
                if (!object[signalName].slots) return;
                var idx = object[signalName].slots.indexOf(callback);
                if (idx !== -1) {
                    object[signalName].slots.splice(idx, 1);
                }
            }
        };
    });

    this.signalEmitted = function(signalId, args) {
        data.signals.forEach(function(signal) {
            if (signal[1] === signalId) {
                var signalName = signal[0];
                if (object[signalName] && object[signalName].slots) {
                    object[signalName].slots.forEach(function(slot) {
                        slot.apply(slot, args);
                    });
                }
            }
        });
    };
}
