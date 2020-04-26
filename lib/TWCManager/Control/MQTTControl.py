from termcolor import colored
from ww import f

class MQTTControl:

    import paho.mqtt.client as mqtt
    import _thread


    brokerIP = None
    brokerPort = 1883
    client = None
    config = None
    configConfig = None
    configMQTT = None
    connectionState = 0
    debugLevel = 0
    master = None
    password = None
    status = False
    serverTLS = False
    topicPrefix = None
    username = None

    def __init__(self, master):
        self.config = master.config
        try:
            self.configConfig = self.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configMQTT = self.config["control"]["MQTT"]
        except KeyError:
            self.configMQTT = {}
        self.debugLevel = self.configConfig.get("debugLevel", 0)
        self.status = self.configMQTT.get("enabled", False)
        self.brokerIP = self.configMQTT.get("brokerIP", None)
        self.master = master
        self.topicPrefix = self.configMQTT.get("topicPrefix", None)
        self.username = self.configMQTT.get("username", None)
        self.password = self.configMQTT.get("password", None)

        # Subscribe to the specified topic prefix, and process incoming messages
        # to determine if they represent control messages
        self.master.debugLog(10, "MQTTCtrl", "Attempting to Connect")
        if self.brokerIP:
            self.client = self.mqtt.Client("MQTTCtrl")
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            self.client.on_connect = self.mqttConnect
            self.client.on_message = self.mqttMessage
            self.client.on_subscribe = self.mqttSubscribe
            try:
                self.client.connect_async(
                    self.brokerIP, port=self.brokerPort, keepalive=30
                )
            except ConnectionRefusedError as e:
                self.master.debugLog(4, "MQTTCtrl", "Error connecting to MQTT Broker")
                self.master.debugLog(10, "MQTTCtrl", str(e))
                return False
            except OSError as e:
                self.master.debugLog(4, "MQTTCtrl", "Error connecting to MQTT Broker")
                self.master.debugLog(10, "MQTTCtrl", str(e))
                return False

            self.connectionState = 1
            self.client.loop_start()

        else:
            self.master.debugLog(4, "MQTTCtrl", "Module enabled but no brokerIP specified.")

    def mqttConnect(self, client, userdata, flags, rc):
        self.master.debugLog(5, "MQTTCtrl", "MQTT Connected.")
        self.master.debugLog(5, "MQTTCtrl", "Subscribe to " + self.topicPrefix + "/#")
        res = self.client.subscribe(self.topicPrefix + "/#", qos=0)
        self.master.debugLog(5, "MQTTCtrl", "Res: " + str(res))

    def mqttMessage(self, client, userdata, message):

        # Takes an MQTT message which has a message body of the following format:
        # [Amps to charge at],[Seconds to charge for]
        # eg. 24,3600
        if message.topic == self.topicPrefix + "/control/chargeNow":
            payload = str(message.payload.decode("utf-8"))
            self.master.debugLog(3, "MQTTCtrl", "MQTT Message called chargeNow with payload " + payload)
            plsplit = payload.split(",", 1)
            if len(plsplit) == 2:
                self.master.setChargeNowAmps(int(plsplit[0]))
                self.master.setChargeNowTimeEnd(int(plsplit[1]))
            else:
                self.master.debugLog(
                    1, "MQTT chargeNow command failed: Expecting comma seperated string in format amps,seconds"
                )

        if message.topic == self.topicPrefix + "/control/chargeNowEnd":
            self.master.debugLog(3, "MQTTCtrl", "MQTT Message called chargeNowEnd")
            self.master.resetChargeNowAmps()

        if message.topic == self.topicPrefix + "/control/stop":
            self.master.debugLog(3, "MQTTCtrl", "MQTT Message called Stop")
            self._thread.interrupt_main()

    def mqttSubscribe(self, client, userdata, mid, granted_qos):
        self.master.debugLog(1, "MQTTCtrl", "Subscribe operation completed with mid " + str(mid))
