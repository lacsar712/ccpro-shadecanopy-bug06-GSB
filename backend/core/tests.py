"""角色 × 写路径一致性回归测试。

约定：
- 错令牌/无令牌一律 401；已登录无权限一律 403。
- 管理员全部写入口可用；种植员可改温室备注类字段、可新建分区/气候/轮灌，
  不可改温室名称、不可新建/删除温室。
- 同一枚令牌下，登录回包、/auth/me/、各写入口认成同一人。
"""
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import ClimateLog, Greenhouse, IrrigationCycle, Zone

User = get_user_model()

TOKEN_URL = "/api/auth/token/"
ME_URL = "/api/auth/me/"
GH_LIST = "/api/greenhouses/"
ZONE_LIST = "/api/zones/"
CLIMATE_LIST = "/api/climate-logs/"
IRRIGATION_LIST = "/api/irrigation-cycles/"


class RoleWritePathTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="admin", password="123456", role=User.ROLE_ADMIN
        )
        cls.grower = User.objects.create_user(
            username="grower", password="123456", role=User.ROLE_GROWER
        )
        cls.greenhouse = Greenhouse.objects.create(
            name="东坡一号棚", location="东区 A 排", area_m2="1200.00", notes="原备注"
        )
        cls.zone = Zone.objects.create(
            greenhouse=cls.greenhouse, zone_code="A-01", crop_name="樱桃番茄"
        )

    # ---------- helpers ----------

    def token_for(self, username):
        resp = self.client.post(
            TOKEN_URL, {"username": username, "password": "123456"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        return resp

    def auth_as(self, username):
        resp = self.token_for(username)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}"
        )
        return resp

    # ---------- 身份一致性 ----------

    def test_login_response_and_me_identify_same_user(self):
        for username in ("admin", "grower"):
            login = self.token_for(username)
            self.assertEqual(login.data["user"]["username"], username)
            token_user_id = login.data["user"]["id"]

            self.client.credentials(
                HTTP_AUTHORIZATION=f"Bearer {login.data['access']}"
            )
            me = self.client.get(ME_URL)
            self.assertEqual(me.status_code, status.HTTP_200_OK, me.content)
            self.assertEqual(me.data["username"], username)
            self.assertEqual(me.data["id"], token_user_id)
            self.client.credentials()

    def test_me_never_returns_another_user(self):
        # 回归：旧实现拿 token 的 user_id 当 username 查库 → 401 或错人。
        login = self.auth_as("grower")
        me = self.client.get(ME_URL)
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["username"], "grower")
        self.assertEqual(me.data["id"], login.data["user"]["id"])

    # ---------- 401 矩阵 ----------

    def test_bad_token_is_401_everywhere(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        for url in (ME_URL, GH_LIST, ZONE_LIST, CLIMATE_LIST, IRRIGATION_LIST):
            self.assertEqual(
                self.client.get(url).status_code,
                status.HTTP_401_UNAUTHORIZED,
                url,
            )
        self.assertEqual(
            self.client.patch(
                f"{GH_LIST}{self.greenhouse.id}/", {"notes": "x"}, format="json"
            ).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_anonymous_write_is_401(self):
        self.assertEqual(
            self.client.post(GH_LIST, {"name": "新棚"}, format="json").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.patch(
                f"{GH_LIST}{self.greenhouse.id}/", {"notes": "x"}, format="json"
            ).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    # ---------- 温室写路径 ----------

    def test_admin_can_rename_greenhouse(self):
        self.auth_as("admin")
        resp = self.client.patch(
            f"{GH_LIST}{self.greenhouse.id}/", {"name": "改名棚"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.greenhouse.refresh_from_db()
        self.assertEqual(self.greenhouse.name, "改名棚")

    def test_grower_cannot_rename_greenhouse(self):
        self.auth_as("grower")
        resp = self.client.patch(
            f"{GH_LIST}{self.greenhouse.id}/", {"name": "改名棚"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN, resp.content)
        self.greenhouse.refresh_from_db()
        self.assertEqual(self.greenhouse.name, "东坡一号棚")

    def test_grower_can_update_notes(self):
        self.auth_as("grower")
        resp = self.client.patch(
            f"{GH_LIST}{self.greenhouse.id}/",
            {"notes": "种植员补充的备注"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.greenhouse.refresh_from_db()
        self.assertEqual(self.greenhouse.notes, "种植员补充的备注")

    def test_grower_cannot_create_greenhouse(self):
        self.auth_as("grower")
        resp = self.client.post(
            GH_LIST,
            {"name": "新棚", "location": "西区", "areaM2": "100.00", "notes": ""},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN, resp.content)

    def test_grower_cannot_delete_greenhouse(self):
        self.auth_as("grower")
        resp = self.client.delete(f"{GH_LIST}{self.greenhouse.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN, resp.content)
        self.assertTrue(Greenhouse.objects.filter(id=self.greenhouse.id).exists())

    def test_admin_can_create_and_delete_greenhouse(self):
        self.auth_as("admin")
        resp = self.client.post(
            GH_LIST,
            {"name": "新棚", "location": "西区", "areaM2": "100.00", "notes": ""},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        new_id = resp.data["id"]
        self.assertEqual(
            self.client.delete(f"{GH_LIST}{new_id}/").status_code,
            status.HTTP_204_NO_CONTENT,
        )

    # ---------- 分区 / 气候 / 轮灌 ----------

    def test_grower_can_create_zone_climate_irrigation(self):
        self.auth_as("grower")
        zone = self.client.post(
            ZONE_LIST,
            {"greenhouseId": self.greenhouse.id, "zoneCode": "A-09", "status": "idle"},
            format="json",
        )
        self.assertEqual(zone.status_code, status.HTTP_201_CREATED, zone.content)

        climate = self.client.post(
            CLIMATE_LIST,
            {
                "zoneId": self.zone.id,
                "recordedAt": "2026-09-21T08:00:00+08:00",
                "tempC": "24.50",
                "humidityPct": "68.00",
                "parUmol": "420.00",
                "co2Ppm": "650.00",
            },
            format="json",
        )
        self.assertEqual(climate.status_code, status.HTTP_201_CREATED, climate.content)

        irrigation = self.client.post(
            IRRIGATION_LIST,
            {
                "zoneId": self.zone.id,
                "startAt": "2026-09-21T10:00:00+08:00",
                "durationMin": 25,
                "waterLiters": "180.00",
                "status": "scheduled",
            },
            format="json",
        )
        self.assertEqual(
            irrigation.status_code, status.HTTP_201_CREATED, irrigation.content
        )

    def test_admin_can_create_zone_climate_irrigation(self):
        self.auth_as("admin")
        self.assertEqual(
            self.client.post(
                ZONE_LIST,
                {
                    "greenhouseId": self.greenhouse.id,
                    "zoneCode": "A-10",
                    "status": "idle",
                },
                format="json",
            ).status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            self.client.post(
                CLIMATE_LIST,
                {
                    "zoneId": self.zone.id,
                    "recordedAt": "2026-09-21T08:00:00+08:00",
                    "tempC": "24.50",
                    "humidityPct": "68.00",
                },
                format="json",
            ).status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            self.client.post(
                IRRIGATION_LIST,
                {
                    "zoneId": self.zone.id,
                    "startAt": "2026-09-21T10:00:00+08:00",
                    "durationMin": 25,
                    "waterLiters": "180.00",
                },
                format="json",
            ).status_code,
            status.HTTP_201_CREATED,
        )

    # ---------- 数据落库校验 ----------

    def test_writes_persist_for_both_roles(self):
        self.assertEqual(ClimateLog.objects.count(), 0)
        self.assertEqual(IrrigationCycle.objects.count(), 0)
        self.test_grower_can_create_zone_climate_irrigation()
        self.assertEqual(ClimateLog.objects.count(), 1)
        self.assertEqual(IrrigationCycle.objects.count(), 1)
