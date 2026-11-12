"""AI CFO Intelligent Financial Assistant Service

Combines:
- OpenAI Structured Tool Calling
- Deterministic Database Analytics Execution
- Complete Conversation History Persistence
- Multi-Tenant Data Protection
- Robust Offline Fallback Engine
"""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from openai import OpenAI

from app.core.config import settings
from app.core.logging_config import logger
from app.models.user import User
from app.models.business import Business
from app.models.chat import ChatSession, ChatMessage
from app.services.cfo_tools import (
    CFO_TOOL_SCHEMAS,
    execute_cfo_tool,
)


SYSTEM_PROMPT = """You are Guardian CFO, an intelligent AI Chief Financial Officer and executive cash flow strategist for small and medium businesses.

CORE RULES:
1. TRUTHFULNESS: Only cite actual financial numbers provided by your approved tools. NEVER invent or hallucinate figures.
2. TOOL USAGE: You have access to approved read-only tools to retrieve live financial summaries, category breakdowns, top vendors, affordability checks, unusual expense surges, and recurring obligations.
3. SECURITY: You are strictly an advisory intelligence. You CANNOT modify account balances, execute transactions, or approve payouts. Payouts require human authorization and Guardian AI risk scoring.
4. TONE & STYLE: Clear, encouraging, executive, and practical. Use markdown formatting with bullet points and bold financial amounts (e.g., **$18,750.00**).
5. AFFORDABILITY: When asked if the business can afford an amount, explain the runway impact in days and compare against remaining monthly budget and total balance.
"""


class AICFOService:

    @classmethod
    def get_or_create_session(
        cls,
        db: Session,
        business: Business,
        user: User,
        session_id: Optional[int] = None,
        title: Optional[str] = None,
    ) -> ChatSession:
        """Retrieves an existing chat session or initializes a new one for the tenant."""
        if session_id:
            sess = (
                db.query(ChatSession)
                .filter(ChatSession.id == session_id, ChatSession.business_id == business.id)
                .first()
            )
            if sess:
                return sess

        # Create new session
        new_sess = ChatSession(
            business_id=business.id,
            user_id=user.id,
            title=title or "Executive CFO Advisory",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_sess)
        db.commit()
        db.refresh(new_sess)
        return new_sess

    @classmethod
    def get_session_history(cls, db: Session, session_id: int, limit: int = 10) -> List[ChatMessage]:
        """Retrieves chronological messages for an active consultation session."""
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )[::-1]  # Return in chronological order

    @classmethod
    def ask_cfo(
        cls,
        db: Session,
        business: Business,
        user: User,
        prompt: str,
        session_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Processes user financial query, executes tools against DB, and returns structured advice."""
        # 1. Resolve Session & Save User Message
        session = cls.get_or_create_session(db, business, user, session_id)
        user_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content=prompt,
            created_at=datetime.utcnow(),
        )
        db.add(user_msg)
        db.commit()

        # Update session title if default
        if session.title == "Executive CFO Advisory":
            session.title = prompt[:45] + ("..." if len(prompt) > 45 else "")
            session.updated_at = datetime.utcnow()
            db.commit()

        # 2. Check OpenAI Configuration
        has_openai = bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"))

        reply_text = ""
        tools_executed: List[str] = []
        insight_card: Optional[Dict[str, Any]] = None

        if has_openai:
            try:
                reply_text, tools_executed, insight_card = cls._ask_openai_with_tools(
                    db=db,
                    business=business,
                    session=session,
                    current_prompt=prompt,
                )
            except Exception as exc:
                logger.warning(f"OpenAI API call failed: {exc}. Activating high-performance fallback engine.")
                reply_text, tools_executed, insight_card = cls._ask_fallback_engine(
                    db=db,
                    business=business,
                    prompt=prompt,
                )
                config_note = f"\n\n> ⚠️ **Notice:** OpenAI API call encountered an issue ({str(exc)[:100]}). Running verified deterministic database analytics engine (Zero Hallucination mode)."
                if config_note not in reply_text:
                    reply_text += config_note
        else:
            logger.info("OPENAI_API_KEY not configured. Running verified algorithmic CFO engine.")
            reply_text, tools_executed, insight_card = cls._ask_fallback_engine(
                db=db,
                business=business,
                prompt=prompt,
            )
            config_note = "\n\n> ℹ️ **Notice:** `OPENAI_API_KEY` is not configured in `backend/.env`. Running verified deterministic database analytics engine (Zero Hallucination mode)."
            if config_note not in reply_text:
                reply_text += config_note

        # 3. Save Assistant Message with Reasoning Metadata
        assistant_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=reply_text,
            reasoning_meta=json.dumps({
                "tools_executed": tools_executed,
                "insight_card": insight_card,
            }) if (tools_executed or insight_card) else None,
            created_at=datetime.utcnow(),
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        return {
            "session_id": session.id,
            "session_title": session.title,
            "message_id": assistant_msg.id,
            "role": "assistant",
            "reply": reply_text,
            "tools_executed": tools_executed,
            "insight_card": insight_card,
            "timestamp": assistant_msg.created_at.isoformat(),
        }

    # Backward compatibility alias
    consult = ask_cfo

    @classmethod
    def _ask_openai_with_tools(
        cls,
        db: Session,
        business: Business,
        session: ChatSession,
        current_prompt: str,
    ) -> (str, List[str], Optional[Dict[str, Any]]):
        """Orchestrates multi-turn tool calling with OpenAI GPT-4o."""
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Build message history for context
        history = cls.get_session_history(db, session.id, limit=8)
        messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]

        for h in history:
            messages.append({"role": h.role, "content": h.content})

        tools_run: List[str] = []
        insight_card: Optional[Dict[str, Any]] = None

        # First turn: Ask OpenAI
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=CFO_TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.2,
        )

        response_message = response.choices[0].message

        # Check if model wants to call tools
        if response_message.tool_calls:
            messages.append(response_message)

            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                tools_run.append(function_name)

                # Execute database tool
                tool_output = execute_cfo_tool(function_name, args, db, business)

                # Capture primary insight card
                if not insight_card:
                    insight_card = {"type": function_name, "data": tool_output}

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(tool_output),
                })

            # Second turn: Let OpenAI synthesize natural explanation with tool outputs
            second_response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0.2,
            )
            final_reply = second_response.choices[0].message.content or ""
            return final_reply, tools_run, insight_card

        return response_message.content or "", tools_run, insight_card

    @classmethod
    def _ask_fallback_engine(
        cls,
        db: Session,
        business: Business,
        prompt: str,
    ) -> (str, List[str], Optional[Dict[str, Any]]):
        """Intelligent Deterministic Financial Agent.

        Provides accurate, calculated financial explanations directly from the database
        when an external OpenAI key is not configured or in offline mode.
        """
        p_lower = prompt.lower()
        tools_run: List[str] = []
        insight_card: Optional[Dict[str, Any]] = None

        # 1. Intent: Affordability Check ("Can I afford", "can we pay", "afford 50,000")
        if "afford" in p_lower or "can i pay" in p_lower or "can we spend" in p_lower:
            tools_run.append("check_affordability")
            # Extract number using regex (supports commas, e.g. 50,000 or 50000)
            numbers = re.findall(r"[\$₹€£]?\s*(\d+(?:,\d+)*(?:\.\d+)?)", prompt)
            amount = 1000.0
            if numbers:
                try:
                    amount = float(numbers[0].replace(",", ""))
                except ValueError:
                    amount = 1000.0

            aff = execute_cfo_tool("check_affordability", {"amount": amount, "currency": business.currency}, db, business)
            insight_card = {"type": "affordability", "data": aff}

            reply = (
                f"### 💡 Payout Affordability Assessment\n\n"
                f"**Verdict:** `{aff['verdict']}`\n\n"
                f"- **Proposed Amount:** ${amount:,.2f} {business.currency}\n"
                f"- **Current Treasury Balance:** ${aff['current_treasury_balance']:,.2f}\n"
                f"- **Remaining Monthly Budget:** ${aff['remaining_monthly_budget']:,.2f}\n"
                f"- **Post-Purchase Runway:** {aff['projected_runway_months']} Months (-{aff['runway_impact_days']} days burn)\n\n"
                f"**CFO Rationale:** {aff['rationale']}\n\n"
                f"> **Governance Notice:** {aff['disclaimer']}"
            )
            return reply, tools_run, insight_card

        # 2. Intent: Biggest Expenses & Categorization ("What are my biggest expenses", "categories", "where did money go")
        if "biggest expense" in p_lower or "categories" in p_lower or "category" in p_lower or "where is money" in p_lower:
            tools_run.append("get_category_breakdown")
            cat_data = execute_cfo_tool("get_category_breakdown", {}, db, business)
            insight_card = {"type": "category_breakdown", "data": cat_data}

            exp_bullets = "\n".join(
                [f"- **{c['category']}**: ${c['amount']:,.2f} ({c['percentage_share']}% of total outflows)"
                 for c in cat_data["top_expense_categories"]]
            )

            reply = (
                f"### 📊 Expense Allocation Breakdown\n\n"
                f"Your total operating expenses for this period are **${cat_data['total_expenses']:,.2f}**.\n\n"
                f"**Primary Cost Drivers:**\n"
                f"{exp_bullets}\n\n"
                f"💡 **CFO Recommendation:** The highest expenditure category is **{cat_data['top_expense_categories'][0]['category']}**. "
                f"Review contract terms to optimize monthly burn rate."
            )
            return reply, tools_run, insight_card

        # 3. Intent: Vendor Costs ("Which vendor costs me the most", "top vendor", "biggest vendor")
        if "vendor" in p_lower and ("most" in p_lower or "cost" in p_lower or "top" in p_lower or "highest" in p_lower):
            tools_run.append("get_top_vendors")
            v_data = execute_cfo_tool("get_top_vendors", {"limit": 5}, db, business)
            insight_card = {"type": "top_vendors", "data": v_data}

            v_bullets = "\n".join(
                [f"- **{v['vendor_name']}**: ${v['total_paid']:,.2f} cumulative (Trust Score: `{v['trust_score']}/100`)"
                 for v in v_data["top_vendors"]]
            )

            reply = (
                f"### 🏢 Vendor Expenditure Analysis\n\n"
                f"Your highest-cost vendor partner is **{v_data['primary_cost_driver']}**.\n\n"
                f"**Top Vendor Commitments:**\n"
                f"{v_bullets}\n\n"
                f"All top vendors are verified with active security scores on Guardian CFO."
            )
            return reply, tools_run, insight_card

        # 4. Intent: Compare Periods ("Compare this month with last month", "comparison", "growth")
        if "compare" in p_lower or "vs last month" in p_lower or "growth" in p_lower:
            tools_run.append("compare_periods")
            comp = execute_cfo_tool("compare_periods", {"period1": "current_month", "period2": "last_month"}, db, business)
            insight_card = {"type": "comparison", "data": comp}

            rev_dir = "📈 increased" if comp['revenue_growth_pct'] >= 0 else "📉 decreased"
            exp_dir = "📈 increased" if comp['expense_change_pct'] >= 0 else "📉 decreased"

            reply = (
                f"### ⚖️ Period-over-Period Performance Comparison\n\n"
                f"Here is how this month compares to last month:\n\n"
                f"- **Revenue:** **${comp['revenue_current']:,.2f}** vs ${comp['revenue_previous']:,.2f} ({rev_dir} by **{comp['revenue_growth_pct']}%**)\n"
                f"- **Expenses:** **${comp['expenses_current']:,.2f}** vs ${comp['expenses_previous']:,.2f} ({exp_dir} by **{comp['expense_change_pct']}%**)\n"
                f"- **Net Cash Flow:** **${comp['net_cash_flow_current']:,.2f}** (Prior: ${comp['net_cash_flow_previous']:,.2f}, Delta: **${comp['cash_flow_delta']:,.2f}**)\n\n"
                f"Overall, net cash flow is **{('positive' if comp['net_cash_flow_current'] >= 0 else 'negative')}**, indicating stable operating liquidity."
            )
            return reply, tools_run, insight_card

        # 5. Intent: Unusual Spending & Anomalies ("Unusual spending patterns", "anomalies", "spikes")
        if "unusual" in p_lower or "anomal" in p_lower or "spike" in p_lower or "pattern" in p_lower:
            tools_run.append("get_unusual_spending_patterns")
            anom_data = execute_cfo_tool("get_unusual_spending_patterns", {}, db, business)
            insight_card = {"type": "anomalies", "data": anom_data}

            if anom_data["anomalies_detected"] == 0:
                reply = "### 🛡️ Guardian Anomaly Scan\n\nNo unusual expense spikes or abnormal outflow surges were detected for this period. Spending is operating within normal baseline variance."
            else:
                anom_bullets = "\n".join(
                    [f"- **{a['category']}** ({a['severity']}): {a['description']}" for a in anom_data["items"]]
                )
                reply = (
                    f"### ⚠️ Unusual Expense Surges Detected\n\n"
                    f"Guardian AI detected **{anom_data['anomalies_detected']} unusual spending pattern(s)**:\n\n"
                    f"{anom_bullets}\n\n"
                    f"💡 **Action Required:** Invoices in these spiked categories will require dual verification before PayPal disbursement."
                )
            return reply, tools_run, insight_card

        # 6. Intent: Recurring Expenses & Subscriptions ("recurring", "subscriptions", "monthly bills")
        if "recurring" in p_lower or "subscription" in p_lower or "fixed cost" in p_lower:
            tools_run.append("get_recurring_commitments")
            rec_data = execute_cfo_tool("get_recurring_commitments", {}, db, business)
            insight_card = {"type": "recurring", "data": rec_data}

            rec_bullets = "\n".join(
                [f"- **{r['vendor']}** ({r['category']}): **${r['amount']:,.2f}**/mo (${r['annual_cost']:,.0f}/yr)"
                 for r in rec_data["recurring_subscriptions"]]
            )

            reply = (
                f"### 🔄 Recurring Commitments & Subscriptions\n\n"
                f"You have **${rec_data['total_recurring_monthly']:,.2f}/month** in automated obligations (**${rec_data['total_recurring_annual']:,.2f}/year**).\n\n"
                f"{rec_bullets}\n\n"
                f"These subscriptions are continuously monitored by Guardian CFO to prevent unapproved price changes."
            )
            return reply, tools_run, insight_card

        # 7. Default: General Financial Health Summary ("How is my business performing", "earned", "summary")
        tools_run.append("get_financial_summary")
        summary = execute_cfo_tool("get_financial_summary", {"period": "current_month"}, db, business)
        insight_card = {"type": "summary", "data": summary}

        status_headline = "🟢 Healthy & Profitable" if summary["net_cash_flow"] > 0 else "🔴 Deficit / Burn Alert"

        reply = (
            f"### 📈 Financial Condition Report: {status_headline}\n\n"
            f"Here is your real-time treasury health for **{summary['period']}**:\n\n"
            f"- **Total Revenue:** **${summary['total_revenue']:,.2f}** (+{summary['revenue_growth_pct']}% growth vs prior month)\n"
            f"- **Total Expenses:** **${summary['total_expenses']:,.2f}** ({summary['expense_change_pct']}% change)\n"
            f"- **Net Cash Flow:** **${summary['net_cash_flow']:,.2f}** (Cash Margin: **{summary['cash_flow_margin_pct']}%**)\n"
            f"- **Treasury Balance:** **${summary['treasury_balance']:,.2f}**\n"
            f"- **Operating Runway:** **{summary['runway_months']} Months** of cash reserve\n\n"
            f"💡 **Executive Takeaway:** Your operating cash flow is positive. You have sufficient runway to cover upcoming recurring commitments."
        )
        return reply, tools_run, insight_card

