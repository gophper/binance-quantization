# -*- coding: utf-8 -*-
"""通知系统 - 钉钉通知"""

import requests
import logging
import json
from typing import Dict, Optional
from datetime import datetime
from config import DINGDING_WEBHOOK

logger = logging.getLogger(__name__)

class DingDingNotifier:
    """钉钉通知器"""

    def __init__(self, webhook_url: str = DINGDING_WEBHOOK):
        """
        初始化钉钉通知器

        Args:
            webhook_url: 钉钉机器人webhook URL
        """
        self.webhook_url = webhook_url

    def send_message(self, text: str, title: str = "交易系统通知") -> bool:
        """
        发送文本消息

        Args:
            text: 消息内容
            title: 消息标题

        Returns:
            True if 成功, False if 失败
        """
        if not self.webhook_url:
            logger.warning("DingDing webhook URL is not configured")
            return False

        try:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n\n{text}"
                }
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=5
            )

            if response.status_code == 200:
                logger.info(f"DingDing message sent: {title}")
                return True
            else:
                logger.error(f"DingDing notification failed: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending DingDing message: {str(e)}")
            return False

    def send_buy_signal(self, symbol: str, price: float, confidence: float,
                       reasons: list) -> bool:
        """
        发送买入信号通知

        Args:
            symbol: 交易对
            price: 价格
            confidence: 信心度
            reasons: 信号原因列表

        Returns:
            True if 成功
        """
        text = f"""
🟢 买入信号

交易对: {symbol}
入场价格: {price:.2f}
信心度: {confidence:.0%}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

信号原因:
{self._format_reasons(reasons)}
        """.strip()

        return self.send_message(text, "🚀 买入信号")

    def send_sell_signal(self, symbol: str, price: float, confidence: float,
                        reasons: list) -> bool:
        """
        发送卖出信号通知

        Args:
            symbol: 交易对
            price: 价格
            confidence: 信心度
            reasons: 信号原因列表

        Returns:
            True if 成功
        """
        text = f"""
🔴 卖出信号

交易对: {symbol}
出场价格: {price:.2f}
信心度: {confidence:.0%}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

信号原因:
{self._format_reasons(reasons)}
        """.strip()

        return self.send_message(text, "🛑 卖出信号")

    def send_risk_warning(self, warning_type: str, details: str) -> bool:
        """
        发送风险警告

        Args:
            warning_type: 警告类型 (如 'stop_loss', 'drawdown', 'daily_loss')
            details: 详细信息

        Returns:
            True if 成功
        """
        text = f"""
⚠️ 风险警告

警告类型: {warning_type}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

详情:
{details}
        """.strip()

        return self.send_message(text, "⚠️ 风险警告")

    def send_trade_report(self, trade_data: Dict) -> bool:
        """
        发送交易报告

        Args:
            trade_data: 交易数据字典

        Returns:
            True if 成功
        """
        text = f"""
📊 交易报告

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
交易对: {trade_data.get('symbol', 'N/A')}
交易方向: {trade_data.get('direction', 'N/A')}
入场价格: {trade_data.get('entry_price', 'N/A')}
数量: {trade_data.get('quantity', 'N/A')}
止盈价格: {trade_data.get('take_profit', 'N/A')}
止损价格: {trade_data.get('stop_loss', 'N/A')}

原因: {trade_data.get('reason', 'N/A')}
        """.strip()

        return self.send_message(text, "📊 交易报告")

    def send_daily_summary(self, summary_data: Dict) -> bool:
        """
        发送日报总结

        Args:
            summary_data: 汇总数据

        Returns:
            True if 成功
        """
        text = f"""
📈 每日总结

日期: {datetime.now().strftime('%Y-%m-%d')}
初始资金: {summary_data.get('initial_capital', 'N/A'):.2f}
当前资金: {summary_data.get('current_capital', 'N/A'):.2f}
日收益: {summary_data.get('daily_return', 'N/A')}
累计收益: {summary_data.get('cumulative_return', 'N/A')}

总交易数: {summary_data.get('total_trades', 'N/A')}
盈利交易: {summary_data.get('winning_trades', 'N/A')}
亏损交易: {summary_data.get('losing_trades', 'N/A')}
胜率: {summary_data.get('win_rate', 'N/A')}

持仓数: {summary_data.get('open_positions', 'N/A')}
未实现盈亏: {summary_data.get('unrealized_pnl', 'N/A')}
最大回撤: {summary_data.get('max_drawdown', 'N/A')}
        """.strip()

        return self.send_message(text, "📈 每日总结")

    def send_error_alert(self, error_type: str, error_msg: str) -> bool:
        """
        发送错误警报

        Args:
            error_type: 错误类型
            error_msg: 错误消息

        Returns:
            True if 成功
        """
        text = f"""
❌ 系统错误

错误类型: {error_type}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

错误信息:
{error_msg}
        """.strip()

        return self.send_message(text, "❌ 系统错误")

    @staticmethod
    def _format_reasons(reasons: list) -> str:
        """格式化原因列表"""
        if not reasons:
            return "无"
        return "\n".join([f"• {reason}" for reason in reasons])


class NotificationManager:
    """通知管理器"""

    def __init__(self, webhook_url: str = DINGDING_WEBHOOK):
        """初始化通知管理器"""
        self.dingding = DingDingNotifier(webhook_url)
        self.notifications_sent = []

    def notify_buy_signal(self, signal) -> bool:
        """通知买入信号"""
        result = self.dingding.send_buy_signal(
            symbol=signal.symbol,
            price=signal.price,
            confidence=signal.confidence,
            reasons=signal.reasons
        )

        if result:
            self.notifications_sent.append({
                'type': 'BUY',
                'symbol': signal.symbol,
                'price': signal.price,
                'timestamp': datetime.now()
            })

        return result

    def notify_sell_signal(self, signal) -> bool:
        """通知卖出信号"""
        result = self.dingding.send_sell_signal(
            symbol=signal.symbol,
            price=signal.price,
            confidence=signal.confidence,
            reasons=signal.reasons
        )

        if result:
            self.notifications_sent.append({
                'type': 'SELL',
                'symbol': signal.symbol,
                'price': signal.price,
                'timestamp': datetime.now()
            })

        return result

    def notify_risk_warning(self, warning_type: str, details: str) -> bool:
        """通知风险警告"""
        return self.dingding.send_risk_warning(warning_type, details)

    def notify_error(self, error_type: str, error_msg: str) -> bool:
        """通知系统错误"""
        return self.dingding.send_error_alert(error_type, error_msg)

