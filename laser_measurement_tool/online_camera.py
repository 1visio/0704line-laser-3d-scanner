"""Standalone HIKROBOT online line-laser acquisition and reconstruction app."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from app_config import DEFAULT_CONFIG_PATH, AppConfigError, load_app_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="海康在线线激光三维截面程序")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="使用合成相机验证界面、算法和录制，不加载 MVS SDK",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    app = QApplication(sys.argv)
    try:
        config = load_app_config(args.config)
        from online.window import OnlineCameraWindow

        window = OnlineCameraWindow(config, simulate=args.simulate)
    except (AppConfigError, RuntimeError, ValueError, OSError) as error:
        QMessageBox.critical(None, "在线程序启动失败", str(error))
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
