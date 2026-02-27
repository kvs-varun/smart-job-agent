from flask import Blueprint, jsonify, request

billing_bp = Blueprint("billing", __name__, url_prefix="/billing")


@billing_bp.route("/plans", methods=["GET"])
def list_plans():
    return jsonify({
        "plans": [
            {"id": "free", "name": "Free", "price_inr": 0, "limits": {"final_pdfs_per_day": 3}},
            {"id": "pro", "name": "Pro (stub)", "price_inr": 199, "limits": {"final_pdfs_per_day": 25}},
        ],
        "notes": "Billing is a stub. Integrate Stripe/PayPal later and enforce limits server-side.",
    })


@billing_bp.route("/checkout", methods=["POST"])
def create_checkout():
    data = request.json or {}
    plan_id = data.get("plan_id", "free")
    return jsonify({
        "message": "checkout_stub",
        "plan_id": plan_id,
        "next": "Integrate Stripe Checkout or Razorpay. Do not store card data.",
    })
