import json
import os
import re
from typing import Dict, Optional, Any

class PersonaHandler:
    def __init__(self):
        self.personas_file = "personas.json"
        self.personas = self._load_personas()
        
    def _load_personas(self) -> Dict[str, Any]:
        """Load personas from file or create empty structure"""
        try:
            if os.path.exists(self.personas_file):
                with open(self.personas_file, 'r') as f:
                    data = json.load(f)
                    # Ensure the new structure exists
                    if "premium_roles" not in data:
                        data["premium_roles"] = []
                    return data
            return {"global": None, "users": {}, "premium_roles": []}
        except Exception as e:
            print(f"Error loading personas: {e}")
            return {"global": None, "users": {}, "premium_roles": []}
    
    def _save_personas(self):
        """Save personas to file"""
        try:
            with open(self.personas_file, 'w') as f:
                json.dump(self.personas, f, indent=2)
        except Exception as e:
            print(f"Error saving personas: {e}")
    
    def _sanitize_persona(self, persona: str) -> str:
        """Sanitize persona input to prevent abuse"""
        # Remove potential harmful content
        blocked_patterns = [
            r'hack|exploit|attack|breach|penetrate|inject|script|malware|virus',
            r'conspiracy|illuminati|qanon|deepstate|lizard|reptilian',
            r'self-harm|suicide|kill|murder|violence|torture|abuse',
            r'illegal|drug|weapon|bomb|terrorist|nazi|hitler',
            r'override|system|admin|root|sudo|password|token|key',
            r'ignore.*previous.*instruction|disregard.*prompt|forget.*identity'
        ]
        
        original_persona = persona
        persona_lower = persona.lower()
        
        for pattern in blocked_patterns:
            if re.search(pattern, persona_lower):
                raise ValueError("Persona contains inappropriate content. Please use a different description.")
        
        # Length limits
        if len(persona) > 500:
            raise ValueError("Persona description too long. Please keep it under 500 characters.")
        
        if len(persona.strip()) < 10:
            raise ValueError("Persona description too short. Please provide at least 10 characters.")
        
        return persona.strip()
    
    def set_global_persona(self, persona: str) -> str:
        """Set global persona for all users"""
        try:
            sanitized = self._sanitize_persona(persona)
            self.personas["global"] = sanitized
            self._save_personas()
            return f"✅ Global persona set successfully!"
        except ValueError as e:
            return f"❌ {str(e)}"
    
    def set_user_persona(self, user_id: str, persona: str) -> str:
        """Set persona for specific user"""
        try:
            sanitized = self._sanitize_persona(persona)
            self.personas["users"][user_id] = sanitized
            self._save_personas()
            return f"✅ Personal persona set successfully!"
        except ValueError as e:
            return f"❌ {str(e)}"
    
    def get_persona(self, user_id: str) -> Optional[str]:
        """Get persona for user (user-specific overrides global)"""
        # Check user-specific persona first
        if user_id in self.personas["users"]:
            return self.personas["users"][user_id]
        
        # Fall back to global persona
        return self.personas["global"]
    
    def remove_user_persona(self, user_id: str) -> str:
        """Remove user-specific persona"""
        if user_id in self.personas["users"]:
            del self.personas["users"][user_id]
            self._save_personas()
            return "✅ Your personal persona has been removed. Luna will now use the default or global persona."
        return "ℹ️ You don't have a personal persona set."
    
    def remove_global_persona(self) -> str:
        """Remove global persona"""
        if self.personas["global"]:
            self.personas["global"] = None
            self._save_personas()
            return "✅ Global persona removed. Luna will now use the default personality."
        return "ℹ️ No global persona is currently set."
    
    def get_status(self, user_id: str) -> str:
        """Get persona status for user"""
        user_persona = self.personas["users"].get(user_id)
        global_persona = self.personas["global"]
        
        status = "**Persona Status:**\n\n"
        
        if user_persona:
            status += f"**Your Personal Persona:** {user_persona[:100]}{'...' if len(user_persona) > 100 else ''}\n\n"
        else:
            status += "**Your Personal Persona:** Not set\n\n"
        
        if global_persona:
            status += f"**Global Persona:** {global_persona[:100]}{'...' if len(global_persona) > 100 else ''}\n\n"
        else:
            status += "**Global Persona:** Not set\n\n"
        
        # Determine what Luna will use
        active_persona = self.get_persona(user_id)
        if active_persona:
            if user_persona:
                status += "**Luna will use:** Your personal persona"
            else:
                status += "**Luna will use:** Global persona"
        else:
            status += "**Luna will use:** Default Luna personality"
        
        return status
    
    def add_premium_role(self, role_id: str) -> str:
        """Add a role to the premium roles list"""
        try:
            role_id = str(role_id)  # Ensure it's a string
            if role_id not in self.personas["premium_roles"]:
                self.personas["premium_roles"].append(role_id)
                self._save_personas()
                return f"✅ Role added to premium persona access!"
            else:
                return f"ℹ️ Role already has premium persona access."
        except Exception as e:
            return f"❌ Error adding role: {str(e)}"
    
    def remove_premium_role(self, role_id: str) -> str:
        """Remove a role from the premium roles list"""
        try:
            role_id = str(role_id)  # Ensure it's a string
            if role_id in self.personas["premium_roles"]:
                self.personas["premium_roles"].remove(role_id)
                self._save_personas()
                return f"✅ Role removed from premium persona access!"
            else:
                return f"ℹ️ Role doesn't have premium persona access."
        except Exception as e:
            return f"❌ Error removing role: {str(e)}"
    
    def has_premium_access(self, user_roles: list) -> bool:
        """Check if user has any of the premium roles"""
        if not self.personas["premium_roles"]:
            return True  # If no premium roles are set, everyone has access
        
        user_role_ids = [str(role.id) for role in user_roles]
        return any(role_id in self.personas["premium_roles"] for role_id in user_role_ids)
    
    def get_premium_roles_list(self) -> str:
        """Get formatted list of premium roles"""
        if not self.personas["premium_roles"]:
            return "ℹ️ No premium roles set. All users can use /setmypersona."
        
        role_list = "\n".join([f"• <@&{role_id}>" for role_id in self.personas["premium_roles"]])
        return f"**Premium Persona Roles:**\n{role_list}"

# Global instance
persona_handler = PersonaHandler()
