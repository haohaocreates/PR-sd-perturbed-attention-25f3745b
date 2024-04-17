try:
    import pag_nodes

    if pag_nodes.BACKEND == "Forge":
        import gradio as gr

        from modules import scripts
        from modules.ui_components import InputAccordion

        opPerturbedAttention = pag_nodes.PerturbedAttention()

        class PerturbedAttentionScript(scripts.Script):
            def title(self):
                return "Perturbed-Attention Guidance"

            def show(self, is_img2img):
                return scripts.AlwaysVisible

            def ui(self, *args, **kwargs):
                with gr.Accordion(open=False, label=self.title()):
                    enabled = gr.Checkbox(label="Enabled", value=False)
                    with gr.Row():
                        scale = gr.Slider(label="Scale", minimum=0.0, maximum=30.0, step=0.01, value=3.0)
                        adaptive_scale = gr.Slider(label="Adaptive Scale", minimum=0.0, maximum=1.0, step=0.001, value=0.0)
                    with InputAccordion(False, label="Override for Hires. fix") as hr_override:
                        hr_cfg = gr.Slider(minimum=1.0, maximum=30.0, step=0.5, label="CFG Scale", value=7.0)
                        hr_scale = gr.Slider(label="PAG Scale", minimum=0.0, maximum=30.0, step=0.01, value=3.0)
                        hr_adaptive_scale = gr.Slider(label="Adaptive Scale", minimum=0.0, maximum=1.0, step=0.001, value=0.0)
                    with gr.Row():
                        block = gr.Dropdown(choices=["input", "middle", "output"], value="middle", label="U-Net Block")
                        block_id = gr.Number(label="U-Net Block Id", value=0, precision=0, minimum=0)

                return enabled, scale, adaptive_scale, block, block_id, hr_override, hr_cfg, hr_scale, hr_adaptive_scale

            def process_before_every_sampling(self, p, *script_args, **kwargs):
                enabled, scale, adaptive_scale, block, block_id, hr_override, hr_cfg, hr_scale, hr_adaptive_scale = script_args

                if not enabled:
                    return

                unet = p.sd_model.forge_objects.unet

                hr_enabled = getattr(p, "enable_hr", False)

                if hr_enabled and p.is_hr_pass and hr_override:
                    p.cfg_scale_before_hr = p.cfg_scale
                    p.cfg_scale = hr_cfg
                    unet = opPerturbedAttention.patch(unet, hr_scale, hr_adaptive_scale, block, block_id)[0]
                else:
                    unet = opPerturbedAttention.patch(unet, scale, adaptive_scale, block, block_id)[0]

                p.sd_model.forge_objects.unet = unet

                p.extra_generation_params.update(
                    dict(
                        pag_enabled=enabled,
                        pag_scale=scale,
                        pag_adaptive_scale=adaptive_scale,
                        pag_block=block,
                        pag_block_id=block_id,
                    )
                )
                if hr_enabled:
                    p.extra_generation_params["pag_hr_override"] = hr_override
                    if hr_override:
                        p.extra_generation_params.update(
                            dict(
                                pag_hr_cfg=hr_cfg,
                                pag_hr_scale=hr_scale,
                                pag_hr_adaptive_scale=hr_adaptive_scale,
                            )
                        )

                return

            def post_sample(self, p, ps, *script_args):
                enabled, scale, adaptive_scale, block, block_id, hr_override, hr_cfg, hr_scale, hr_adaptive_scale = script_args

                if not enabled:
                    return

                hr_enabled = getattr(p, "enable_hr", False)

                if hr_enabled and hr_override:
                    p.cfg_scale = p.cfg_scale_before_hr

                return

except ImportError:
    pass
