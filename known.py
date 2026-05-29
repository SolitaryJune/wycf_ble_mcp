"""Static facts extracted from the APK/Unity bundles.

The ordinary toy-control UUIDs still need one dynamic write log to confirm
which candidate pair is active for each product. Keep candidates separate from
confirmed OTA UUIDs to avoid accidentally using the firmware-upgrade channel.
"""

PRODUCT_IDS = {
    "YXL01": "tf-mastrb8-yxl01",
    "BBW01": "tf-clitsuck-bbw01",
    "LC01": "tf-vibroegg-lc01",
    "BHMINI": "tf-mastrb8-bhmp01",
    "BHPRO": "tf-mastrb8-bhp02",
    "PTPRO": "tf-mastrb8-hqm01",
    "YL02": "tf-mastrb8-yxl02",
    "ROSE": "tf-vibrowand-rose01",
    "CX02": "tf-vibroegg-spr01",
    "BHPLUS": "tf-mastrb8-bhp03",
    "SOULMT": "tf-mastrb8-hqm02",
    "YL02SE": "tf-mastrb8-yxl03",
    "ICEPOP": "tf-vibrowand-ice01",
    "BHMAX": "tf-mastrb8-bhmx01",
    "BHSE": "tf-mastrb8-bhse01",
}

TOY_NAME_PREFIXES = (
    "tf-",
    "tryfun",
)

OTA_SERVICE_UUID = "0000ae00-0000-1000-8000-00805f9b34fb"
OTA_WRITE_UUID = "0000ae01-0000-1000-8000-00805f9b34fb"
OTA_NOTIFY_UUID = "0000ae02-0000-1000-8000-00805f9b34fb"

CONTROL_UUID_CANDIDATES = (
    "0000ff00-0000-1000-8000-00805f9b34fb",
    "0000ff01-0000-1000-8000-00805f9b34fb",
    "0000ff10-0000-1000-8000-00805f9b34fb",
    "0000ff12-0000-1000-8000-00805f9b34fb",
    "0000ff14-0000-1000-8000-00805f9b34fb",
    "0000ffac-0000-1000-8000-00805f9b34fb",
    "0000ffb4-0000-1000-8000-00805f9b34fb",
    "0000ffb5-0000-1000-8000-00805f9b34fb",
    "0000ffb7-0000-1000-8000-00805f9b34fb",
    "0000ffb8-0000-1000-8000-00805f9b34fb",
    "0000fff1-0000-1000-8000-00805f9b34fb",
)

CONFIRMED_CONTROL_UUIDS = {
    "service": "0000ffac-0000-1000-8000-00805f9b34fb",
    "write": "0000ffb7-0000-1000-8000-00805f9b34fb",
    "write_with_response_observed": "0000ffb5-0000-1000-8000-00805f9b34fb",
    "notify": "0000ffb8-0000-1000-8000-00805f9b34fb",
    "evidence": "TFBLEWrite logcat from com.tryfun.intelligent 8.2.0 controlling Black Hole Max",
}

CONFIRMED_CONTROL_COMMANDS = {
    "telescopic_level": {
        "command_id": 0x0C,
        "frame": "[seq, 0x02, 0x00, 0x03, 0x0c, level, checksum]",
        "checksum": "checksum = -(0x0c + level) & 0xff",
        "examples": {
            "level_0": "000200030c00f4",
            "level_3": "050200030c03f1",
            "level_74": "080200030c4aaa",
        },
    },
    "observed_command_0x05_level_1": {
        "command_id": 0x05,
        "characteristic_uuid": "0000ffb5-0000-1000-8000-00805f9b34fb",
        "payload_hex": "010200030501fa",
        "status": "observed in logcat; maps to the heating switch in the local controller",
    },
}

CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"

TFGTC_BRIDGE_SCHEME = "tfgtc"

TFGTC_COMMANDS = {
    "create_session": "tfgtc://create_session",
    "disconnect": "tfgtc://disconnect?id={session_id}",
    "reconnect": "tfgtc://reconnect?id={session_id}",
    "heartbeat": "tfgtc://change_heartbeat_period?id={session_id}&period={seconds}",
    "stop": "tfgtc://stop?id={session_id}&with_response={with_response}",
    "pause": "tfgtc://pause?id={session_id}",
    "resume": "tfgtc://resume?id={session_id}",
    "execute": "tfgtc://execute?id={session_id}&with_response={with_response}&commands={commands}",
    "get_accessory_id": "tfgtc://get_accessory_id?id={session_id}",
    "get_score_calculation_req_data": "tfgtc://get_score_calculation_req_data?id={session_id}&complete={complete}",
    "get_state": "tfgtc://get_state?id={session_id}",
    "select_product_to_play_with": (
        "tfgtc://select_product_to_play_with?id={session_id}"
        "&connected_product_id={product_id}&limited_product_ids={limited_product_ids}"
    ),
}

TFGTC_STATE_FIELDS = (
    "connected",
    "battery",
    "batteryStatus",
    "isWorking",
    "hasLiner",
    "mode",
    "flag",
    "linerStatus",
    "linerId",
    "linerUsedTime",
    "linerLifeTime",
    "skillId",
    "vibrationLevel",
    "telescopicLevel",
    "rotationLevel",
    "suctionLevel",
    "switchMode",
    "hasGamePad",
    "x",
    "y",
    "z",
    "gyroSwitch",
    "keyCodeEvent",
    "gamePadModeVibrationLevel",
    "gamePadModeTelescopicLevel",
    "gamePadModeRotationLevel",
    "gamePadButtonVibrationTap",
    "gamePadButtonTelescopicTap",
    "gamePadButtonRotationTap",
    "gamePadButtonStopTap",
)
