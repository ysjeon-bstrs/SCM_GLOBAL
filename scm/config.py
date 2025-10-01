from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict

@dataclass(frozen=True)
class Config:
    gsheet_id: str = "1RYjKW2UDJ2kWJLAqQH26eqx2-r9Xb0_qE_hfwu9WIj8"
    arrival_to_inbound_lag_days: int = 7
    center_column_map: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.center_column_map:
            object.__setattr__(
                self,
                "center_column_map",
                {
                    "태광KR": "stock2",
                    "AMZUS": "fba_available_stock",
                    "품고KR": "poomgo_v2_available_stock",
                    "SBSPH": "shopee_ph_available_stock",
                    "SBSSG": "shopee_sg_available_stock",
                    "SBSMY": "shopee_my_available_stock",
                    "AcrossBUS": "acrossb_available_stock",
                    "어크로스비US": "acrossb_available_stock",
                },
            )

DEFAULT_CONFIG = Config()
