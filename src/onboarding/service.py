from typing import Any
from collections import Counter, defaultdict
from .models import UserAction, Action, Onboarding, NextAction
from .repo import OnboardingRepo


class Script:
    def __init__(self, onboarding_repo: OnboardingRepo):
        self._repo = onboarding_repo
        self.actions: list[tuple[Action, Any]] = [
            (Action.SEND_MESSAGE, None),
            (Action.REOPEN_CHAT, None),
            (Action.SEND_MESSAGE, None),
            (Action.CHARGE_SCRATCH_LIGHTS, 20),
            (Action.CLEAR_SCRATCH_LAYER, 20),
            (Action.SEND_MESSAGE, None),
            (Action.CHARGE_PIXEL_LIGHTS, 300),
            (Action.CLEAR_PIXEL_LAYER, 300),
        ]
        self.counter = Counter([action[0] for action in self.actions])

    async def get_next_action(self, user_id: int, last_action: Action | None) -> NextAction | None:
        a_msgs, next_action_idx, meta, skiped_actions = (
            [], 0, None, defaultdict(int)
        )

        if not last_action:
            next_action_idx = 0
        else:
            for idx, _action in enumerate(self.actions):
                action, _ = _action
                skiped_actions[action] += 1
                if action != last_action:
                    continue

                if self.counter[action] > 1:
                    user_actions = len(await self._repo.get_user_actions(user_id, action))
                    if user_actions == skiped_actions[action]:
                        next_action_idx = idx + 1
                        break
                    else:
                        continue
                else:
                    next_action_idx = idx + 1
                    break

        a_msgs = await self._repo.get_assistant_message(next_action_idx)

        try:
            next_action, meta = self.actions[next_action_idx][0], self.actions[next_action_idx][1]
        except IndexError:
            next_action, meta = None, None

        return NextAction(
            action=next_action,
            meta=meta,
            assistant_messages=a_msgs
        )


class OnboardingService:
    def __init__(self):
        self._repo: OnboardingRepo = OnboardingRepo()
        self._script = Script(self._repo)

    async def _get_last_user_action(self, user_id: int) -> UserAction | None:
        user_actions = await self._repo.get_user_actions(user_id)

        try:
            return user_actions[-1]
        except IndexError:
            return None

    async def handle_user_action(self, user_action: UserAction) -> NextAction:
        last_action = await self._get_last_user_action(user_action.u_id)
        awaitable_user_action = await self._script.get_next_action(
            last_action.u_id if last_action else user_action.u_id,
            last_action.action if last_action else None
        )
        if awaitable_user_action.action != user_action.action:
            return awaitable_user_action

        await self._repo.save_action(user_action)

        return await self._script.get_next_action(user_action.u_id, user_action.action)

    async def get_onboarding(self, user_id: int) -> Onboarding:
        last_action = await self._get_last_user_action(user_id)

        next_action = await self._script.get_next_action(user_id, last_action.action if last_action else None)

        return Onboarding(
            chat=await self._repo.get_chat_history(user_id),
            next_action=next_action
        )
