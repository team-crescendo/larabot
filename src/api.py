import logging
import os
from typing import Tuple

import aiohttp
from dotenv import load_dotenv

load_dotenv(verbose=True, override=True)
base_url = os.getenv("FORTE_BASE_URL")
token = os.getenv("FORTE_TOKEN")

logger = logging.getLogger("lara.api")


async def request(method, endpoint, **kwargs):
    async with aiohttp.request(
        method,
        base_url + endpoint,
        headers={"Authorization": token, "accept": "application/json"},
        **kwargs,
    ) as resp:
        logger.info(f'{method.lower()} "{endpoint}" {resp.status}')
        return await resp.json(), resp


async def get_key_count(discord_id: int) -> int:
    """
    사용자가 보유한 열쇠 개수를 반환합니다.
    포르테에 가입하지 않았거나 출석 기록이 없는 경우 0을 반환합니다.
    """
    result, _ = await request("get", f"/discords/{discord_id}/attendances")
    return result.get("key_count", 0)


class AttendanceError(Exception):
    def __init__(self, level: int, status: str, message: str) -> None:
        self.level = level
        self.status = status
        self.message = message
        super().__init__(message)


async def post_attendace(discord_id: int) -> int:
    """
    출석에 성공했을 경우, 사용자가 보유한 열쇠의 개수를 반환합니다.
    """
    attendance, resp = await request("post", f"/discords/{discord_id}/attendances")

    if attendance.get("error") or resp.status not in (200, 201, 409):
        raise AttendanceError(logging.WARNING, "error", "🔥 에러가 발생했습니다. 잠시 후 다시 시도해주세요.")

    status = attendance.get("status")
    if status == "exist_attendance":
        raise AttendanceError(
            logging.INFO,
            "exist_attendance",
            f"최근에 이미 출석체크 하셨습니다.\n`{attendance.get('diff')}` 후 다시 시도해주세요.",
        )
    elif status == "max_key_count":
        raise AttendanceError(
            logging.INFO,
            "max_key_count",
            "열쇠는 최대 10개까지 가질 수 있습니다.\n`라라야 상자` 명령어를 입력해 열쇠를 사용해주세요.",
        )

    return attendance["key_count"]


async def unpack_box(
    discord_id: int, box_type: str, is_premium: bool
) -> Tuple[int, int]:
    """
    상자를 열고, 획득한 포인트와 남은 열쇠의 개수로 구성된 튜플을 반환합니다.
    """

    if box_type not in ("bronze", "silver", "gold"):
        raise TypeError()

    result, resp = await request(
        "post",
        f"/discords/{discord_id}/attendances/unpack"
        + f"?box={box_type}&isPremium={int(is_premium)}",
    )

    if resp.status == 200:
        return result["point"], result["key_count"]
    elif resp.status in (400, 404):
        raise AttendanceError(logging.INFO, "insufficient_key", "상자를 열기에 충분한 열쇠가 없습니다.")
    else:
        raise AttendanceError(logging.WARNING, "error", "🔥 에러가 발생했습니다. 잠시 후 다시 시도해주세요.")
