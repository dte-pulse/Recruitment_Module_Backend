
import numpy as np
from scipy.optimize import minimize_scalar
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import json


@dataclass
class CATItem:
    """Represents a single CAT item with IRT parameters"""
    id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct: str
    a: float  # Discrimination: 0.5 to 2.0
    b: float  # Difficulty: -3.0 to +3.0  ✓ CONSTRAINED
    c: float  # Guessing: 0.15 to 0.30


@dataclass
class CATResponse:
    """Represents a candidate's response to an item"""
    item_id: int
    selected_option: str
    is_correct: bool
    theta_before: float
    theta_after: float
    se_after: float


class CATEngine:
    """Main CAT Engine implementing adaptive testing logic"""
    
    # ✓ Parameter range constants
    B_MIN = -3.0
    B_MAX = 3.0
    A_MIN = 0.5
    A_MAX = 2.0
    C_MIN = 0.15
    C_MAX = 0.30
    
    def __init__(self, items: List[CATItem], 
                 max_items: int = 20,
                 min_items: int = 20,
                 target_se: float = 0.3,
                 initial_theta: float = 0.0):
        """
        Initialize CAT Engine
        
        Args:
            items: Pool of calibrated CAT items
            max_items: Maximum number of items to administer
            min_items: Minimum number of items before stopping
            target_se: Target standard error for stopping criterion
            initial_theta: Initial ability estimate
        """
        self.items = items
        self.max_items = max_items
        self.min_items = min_items
        self.target_se = target_se
        self.initial_theta = initial_theta
        
        # Session state
        self.current_theta = initial_theta
        self.responses: List[CATResponse] = []
        self.administered_items: List[int] = []
        
    def probability_correct(self, theta: float, a: float, b: float, c: float) -> float:
        """
        Calculate probability of correct response using 3PL model
        P(θ) = c + (1-c) / (1 + exp(-a(θ-b)))
        """
        return c + (1 - c) / (1 + np.exp(-a * (theta - b)))
    
    def item_information(self, theta: float, a: float, b: float, c: float) -> float:
        """
        Calculate Fisher information for an item at given theta
        I(θ) = a² * P(θ) * [1 - P(θ)] / [1 - c]²
        """
        p = self.probability_correct(theta, a, b, c)
        q = 1 - p
        numerator = a**2 * p * q
        denominator = (1 - c)**2
        return numerator / denominator if denominator > 0 else 0
    
    def test_information(self, theta: float, administered_items: List[int]) -> float:
        """Calculate total information from all administered items"""
        total_info = 0
        for item_id in administered_items:
            item = next((i for i in self.items if i.id == item_id), None)
            if item:
                total_info += self.item_information(theta, item.a, item.b, item.c)
        return total_info
    
    def standard_error(self, theta: float, administered_items: List[int]) -> float:
        """
        Calculate standard error of ability estimate
        SE(θ) = 1 / sqrt(I(θ))
        """
        info = self.test_information(theta, administered_items)
        return 1 / np.sqrt(info) if info > 0 else float('inf')
    
    def select_next_item(self) -> Optional[CATItem]:
        """
        Select next item using Maximum Information criterion
        with adaptive difficulty adjustment based on last response
        """
        available_items = [item for item in self.items 
                          if item.id not in self.administered_items]
        
        if not available_items:
            return None
        
        # Apply difficulty window based on recent performance
        if len(self.responses) > 0:
            last_response = self.responses[-1]
            if last_response.is_correct:
                # Filter for harder items (higher b)
                harder_items = [item for item in available_items 
                               if item.b > self.current_theta - 0.5]
                if harder_items:
                    available_items = harder_items
            else:
                # Filter for easier items (lower b)
                easier_items = [item for item in available_items 
                               if item.b < self.current_theta + 0.5]
                if easier_items:
                    available_items = easier_items
        
        # Select item with maximum information
        max_info = -1
        best_item = None
        
        for item in available_items:
            info = self.item_information(self.current_theta, item.a, item.b, item.c)
            if info > max_info:
                max_info = info
                best_item = item
        
        return best_item
    
    def update_theta(self, responses: List[Tuple[int, bool]]) -> float:
        """ 
        Update ability estimate using Maximum Likelihood Estimation (MLE)
        """
        def neg_log_likelihood(theta: float) -> float:
            ll = 0
            for item_id, is_correct in responses:
                item = next((i for i in self.items if i.id == item_id), None)
                if item:
                    p = self.probability_correct(theta, item.a, item.b, item.c)
                    # Avoid log(0)
                    p = max(min(p, 0.9999), 0.0001)
                    ll += is_correct * np.log(p) + (1 - is_correct) * np.log(1 - p)
            return -ll
        
        # Optimize over theta range [-3, 3]
        result = minimize_scalar(neg_log_likelihood, 
                                bounds=(-3, 3), 
                                method='bounded')
        return result.x
    
    def process_response(self, item_id: int, selected_option: str) -> Dict:
        """
        Process a candidate's response and update ability estimate
        """
        item = next((i for i in self.items if i.id == item_id), None)
        if not item:
            raise ValueError(f"Item {item_id} not found")
        
        # Record response
        is_correct = (selected_option.upper() == item.correct.upper())
        theta_before = self.current_theta
        
        # Update theta
        response_list = [(item_id, is_correct)] + [
            (r.item_id, r.is_correct) for r in self.responses
        ]
        theta_after = self.update_theta(response_list)
        self.current_theta = theta_after
        
        # Calculate SE
        self.administered_items.append(item_id)
        se_after = self.standard_error(theta_after, self.administered_items)
        
        # Store response
        cat_response = CATResponse(
            item_id=item_id,
            selected_option=selected_option,
            is_correct=is_correct,
            theta_before=theta_before,
            theta_after=theta_after,
            se_after=se_after
        )
        self.responses.append(cat_response)
        
        return {
            "is_correct": is_correct,
            "theta": round(theta_after, 2),
            "se": round(se_after, 3),
            "num_items": len(self.administered_items)
        }
    
    def should_continue(self) -> bool:
        """
        Determine if testing should continue based on stopping criteria
        """
        num_items = len(self.administered_items)
        
        # Must administer minimum items
        if num_items < self.min_items:
            return True
        
        # Stop if maximum items reached
        if num_items >= self.max_items:
            return False
        
        # Stop if target SE achieved
        se = self.standard_error(self.current_theta, self.administered_items)
        if se <= self.target_se:
            return False
        
        return True
    
    def get_final_results(self) -> Dict:
        """
        Calculate final test results including percentile
        """
        theta = self.current_theta
        se = self.standard_error(theta, self.administered_items)
        
        # Calculate percentile (assuming normal distribution N(0,1))
        from scipy.stats import norm
        percentile = norm.cdf(theta) * 100
        
        # Calculate accuracy
        num_correct = sum(1 for r in self.responses if r.is_correct)
        accuracy = (num_correct / len(self.responses) * 100) if self.responses else 0
        
        return {
            "theta": round(theta, 2),
            "se": round(se, 3),
            "percentile": round(percentile, 1),
            "num_items": len(self.administered_items),
            "num_correct": num_correct,
            "accuracy": round(accuracy, 1),
            "ability_level": self._interpret_theta(theta)
        }
    
    def _interpret_theta(self, theta: float) -> str:
        """Interpret theta score into ability level"""
        if theta < -1.0:
            return "Below Average"
        elif theta < 0.0:
            return "Average"
        elif theta < 1.0:
            return "Above Average"
        elif theta < 2.0:
            return "Excellent"
        else:
            return "Exceptional"
    
    def get_session_state(self) -> Dict:
        """Get current session state for persistence"""
        return {
            "current_theta": self.current_theta,
            "administered_items": self.administered_items,
            "responses": [
                {
                    "item_id": r.item_id,
                    "selected_option": r.selected_option,
                    "is_correct": r.is_correct,
                    "theta_after": r.theta_after
                }
                for r in self.responses
            ]
        }

    @staticmethod
    def recalibrate_item_bank(db_session, min_users: int = 10):
        """
        Recalibrate item parameters (a, b, c) using 3PL IRT model based on user responses.
        Uses 'girth' library if available, otherwise falls back to simple difficulty update.
        
        ✓ FIXED: b parameter now constrained to [-3.0, +3.0]
        """
        try:
            import importlib
            girth_mod = importlib.import_module("girth")
            threepl_mml = getattr(girth_mod, "threepl_mml", None)
        except ImportError:
            threepl_mml = None
            print("⚠️ 'girth' library not found. Falling back to simple calibration.")

        # 1. Fetch all item responses
        import database_models
        
        # Get all items
        all_items = db_session.query(database_models.CATItem).all()
        item_map = {item.id: idx for idx, item in enumerate(all_items)}
        num_items = len(all_items)
        
        # Get all completed sessions with responses
        responses_query = db_session.query(
            database_models.CATItemResponse.session_id,
            database_models.CATItemResponse.item_id,
            database_models.CATItemResponse.is_correct
        ).join(database_models.CATSession).filter(
            database_models.CATSession.is_active == False
        ).all()
        
        if not responses_query:
            print("No completed sessions found for calibration.")
            return

        # Organize data: session_id -> {item_id: is_correct}
        session_responses = {}
        for session_id, item_id, is_correct in responses_query:
            if session_id not in session_responses:
                session_responses[session_id] = {}
            session_responses[session_id][item_id] = 1 if is_correct else 0
            
        num_users = len(session_responses)
        if num_users < min_users:
            print(f"Not enough users for calibration ({num_users}/{min_users}). Skipping.")
            return

        print(f"Starting calibration with {num_users} users and {num_items} items...")

        # 2. Prepare data matrix for girth
        data_matrix = np.full((num_items, num_users), np.nan)
        
        user_ids = list(session_responses.keys())
        for user_idx, session_id in enumerate(user_ids):
            user_resps = session_responses[session_id]
            for item_id, correct in user_resps.items():
                if item_id in item_map:
                    item_idx = item_map[item_id]
                    data_matrix[item_idx, user_idx] = correct

        # 3. Run Calibration
        if threepl_mml:
            try:
                # Filter items that have at least one response
                valid_item_indices = [i for i in range(num_items) if not np.all(np.isnan(data_matrix[i, :]))]
                
                if not valid_item_indices:
                    print("No valid items with responses.")
                    return

                sub_data = data_matrix[valid_item_indices, :]
                
                # Run 3PL MML
                print("Running 3PL MML calibration...")
                results = threepl_mml(sub_data)
                
                # Update items
                updated_count = 0
                for idx, item_idx in enumerate(valid_item_indices):
                    item_db = all_items[item_idx]
                    
                    new_a = max(0.5, float(results['Discrimination'][idx]))
                    new_b = float(results['Difficulty'][idx])
                    new_c = max(0.0, min(0.4, float(results['Guessing'][idx])))
                    
                    # ✓ CONSTRAINT: Force b to [-3.0, +3.0]
                    new_b = max(CATEngine.B_MIN, min(CATEngine.B_MAX, new_b))
                    
                    # Log significant changes
                    if abs(item_db.b - new_b) > 0.1:
                        old_b = item_db.b
                        print(f"Item {item_db.id} (Q: {item_db.question[:30]}...): b {old_b:.2f} → {new_b:.2f}")
                    
                    item_db.a = new_a
                    item_db.b = new_b
                    item_db.c = new_c
                    updated_count += 1
                
                db_session.commit()
                print(f"✓ Calibration complete. Updated {updated_count} items.")
                print(f"  B parameter range: [{CATEngine.B_MIN}, {CATEngine.B_MAX}]")
                return

            except Exception as e:
                print(f"✗ Girth calibration failed: {e}. Falling back to simple update.")
        
        # 4. Fallback: Simple Difficulty Update
        print("Running fallback simple calibration...")
        updated_count = 0
        for item_idx in range(num_items):
            item_row = data_matrix[item_idx, :]
            valid_responses = item_row[~np.isnan(item_row)]
            
            if len(valid_responses) < 5:
                continue
                
            p_correct = np.mean(valid_responses)
            p_correct = max(0.05, min(0.95, p_correct))
            
            # Calculate new b
            new_b = -np.log(p_correct / (1 - p_correct))
            
            # ✓ CONSTRAINT: Force new_b to [-3.0, +3.0]
            new_b = max(CATEngine.B_MIN, min(CATEngine.B_MAX, new_b))
            
            item_db = all_items[item_idx]
            old_b = item_db.b
            
            # Blend with old b to be conservative
            updated_b = 0.8 * old_b + 0.2 * new_b
            
            # ✓ CONSTRAINT AGAIN after blending
            updated_b = max(CATEngine.B_MIN, min(CATEngine.B_MAX, updated_b))
            
            item_db.b = updated_b
            updated_count += 1
            
        db_session.commit()
        print(f"✓ Fallback calibration complete. Updated {updated_count} items.")
        print(f"  B parameter range: [{CATEngine.B_MIN}, {CATEngine.B_MAX}]")


# ============================================================
# VALIDATION HELPER
# ============================================================

def validate_cat_item(item: CATItem) -> Tuple[bool, List[str]]:
    """
    Validate CAT item parameters are within valid ranges
    
    Returns:
        (is_valid: bool, errors: List[str])
    """
    errors = []
    
    # Check b parameter
    if not (CATEngine.B_MIN <= item.b <= CATEngine.B_MAX):
        errors.append(f"B parameter out of range: {item.b} (must be {CATEngine.B_MIN} to {CATEngine.B_MAX})")
    
    # Check a parameter
    if not (CATEngine.A_MIN <= item.a <= CATEngine.A_MAX):
        errors.append(f"A parameter out of range: {item.a} (must be {CATEngine.A_MIN} to {CATEngine.A_MAX})")
    
    # Check c parameter
    if not (CATEngine.C_MIN <= item.c <= CATEngine.C_MAX):
        errors.append(f"C parameter out of range: {item.c} (must be {CATEngine.C_MIN} to {CATEngine.C_MAX})")
    
    if errors:
        return False, errors
    
    return True, []


