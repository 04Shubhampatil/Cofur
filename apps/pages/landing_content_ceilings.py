"""Default wording and photos for the ceilings landing page.

These values seed the LandingText table. After seeding, the admin panel is the
place to edit them; this file is only the starting point.
"""

CEILING_PAGE = "ceilings"

# (key, label, text), in the order they appear on the page.
CEILING_TEXT = [
    ("top_bar", "Announcement bar", "Design-led acoustic wall panel options for commercial interiors · Project enquiries welcome"),
    ("nav_products", "Menu: products link", "Wall panel products"),
    ("nav_applications", "Menu: applications link", "Applications"),
    ("nav_faqs", "Menu: FAQs link", "FAQs"),
    ("nav_quote", "Menu: quote button", "Request project quote"),
    ("hero_eyebrow", "Hero: small label", "Commercial acoustic ceiling solutions"),
    ("hero_title", "Hero: heading", "Acoustic Ceilings for Commercial Offices"),
    ("hero_lead", "Hero: paragraph", "Design-led acoustic ceiling solutions for modern corporate workplaces, meeting rooms, collaborative spaces and commercial interiors."),
    ("hero_check_1", "Hero: check point 1", "Designed for modern commercial workplaces"),
    ("hero_check_2", "Hero: check point 2", "Multiple acoustic ceiling design options"),
    ("hero_check_3", "Hero: check point 3", "Suitable for corporate and commercial projects"),
    ("hero_check_4", "Hero: check point 4", "Project consultation for architects and design teams"),
    ("hero_btn_quote", "Hero: quote button", "Request project quote"),
    ("hero_btn_explore", "Hero: explore button", "Explore designs"),
    ("trust_1", "Strip 1", "Commercial Workspaces"),
    ("trust_2", "Strip 2", "Corporate Projects"),
    ("trust_3", "Strip 3", "Architect Support"),
    ("trust_4", "Strip 4", "Project Consultation"),
    ("products_eyebrow", "Designs: small label", "The collection"),
    ("products_title", "Designs: heading", "Explore COFUR Acoustic Ceiling Designs"),
    ("products_intro", "Designs: paragraph", "Explore different acoustic ceiling forms designed for contemporary commercial workplace environments."),
    ("design_enquire", "Designs: enquire button", "Enquire"),
    ("apps_eyebrow", "Applications: small label", "Applications"),
    ("apps_title", "Applications: heading", "Where Can COFUR Wall Panels Be Considered?"),
    ("apps_intro", "Applications: paragraph", "COFUR lists these wall panel products for corporate, institutional and hospitality spaces."),
    ("apps_1", "Application box 1", "Corporate Offices"),
    ("apps_2", "Application box 2", "Meeting & Conference Areas"),
    ("apps_3", "Application box 3", "Institutional Interiors"),
    ("apps_4", "Application box 4", "Hospitality Spaces"),
    ("apps_5", "Application box 5", "Reception & Common Areas"),
    ("apps_6", "Application box 6", "Commercial Interior Projects"),
    ("aud_eyebrow", "Built for: small label", "Who it is for"),
    ("aud_title", "Built for: heading", "Built for Commercial Workplace Projects"),
    ("aud_text", "Built for: paragraph", "COFUR acoustic ceiling solutions are relevant to professionals involved in designing, specifying and executing workplace projects."),
    ("role_1", "Role 1 label", "Architects"),
    ("role_2", "Role 2 label", "Interior Designers"),
    ("role_3", "Role 3 label", "Corporate Procurement"),
    ("role_4", "Role 4 label", "Facility Managers"),
    ("role_5", "Role 5 label", "Contractors"),
    ("enq_eyebrow", "Enquiry: small label", "Project enquiry"),
    ("enq_title", "Enquiry: heading", "Discuss Your Acoustic Ceiling Project"),
    ("enq_text", "Enquiry: paragraph", "Planning an office, corporate workplace or commercial interior project? Share your requirements with COFUR."),
    ("enq_bullet_1", "Enquiry: bullet 1", "Architects & interior designers"),
    ("enq_bullet_2", "Enquiry: bullet 2", "Corporate procurement teams"),
    ("enq_bullet_3", "Enquiry: bullet 3", "Facility & workplace teams"),
    ("enq_bullet_4", "Enquiry: bullet 4", "Commercial contractors"),
    ("enq_bullet_5", "Enquiry: bullet 5", "Office & commercial projects"),
    ("faq_eyebrow", "FAQ: small label", "Frequently asked questions"),
    ("faq_title", "FAQ: heading", "Frequently Asked Questions"),
    ("faq_q1", "FAQ 1: question", "What are acoustic ceilings?"),
    ("faq_a1", "FAQ 1: answer", "Acoustic ceilings are ceiling solutions designed to address acoustic considerations while also contributing to the visual design of an interior space."),
    ("faq_q2", "FAQ 2: question", "Are acoustic ceilings suitable for commercial offices?"),
    ("faq_a2", "FAQ 2: answer", "Yes. Acoustic ceiling solutions can be considered for corporate offices, commercial workplaces, meeting rooms, collaborative areas and other professional environments."),
    ("faq_q3", "FAQ 3: question", "What acoustic ceiling designs does COFUR offer?"),
    ("faq_a3", "FAQ 3: answer", "The COFUR acoustic ceiling collection includes Wave, Petal, Blade, Planks, Grid, Waffle and Hive designs."),
    ("faq_q4", "FAQ 4: question", "Can architects and interior designers contact COFUR?"),
    ("faq_a4", "FAQ 4: answer", "Yes. Architects, interior designers, procurement teams, contractors and workplace professionals can contact COFUR regarding commercial projects."),
    ("faq_q5", "FAQ 5: question", "Can acoustic ceilings be combined with acoustic lighting?"),
    ("faq_a5", "FAQ 5: answer", "Yes. Acoustic ceiling solutions can be considered alongside acoustic lighting and other workplace acoustic solutions depending on the project."),
    ("faq_q6", "FAQ 6: question", "How can I request an acoustic ceiling quotation?"),
    ("faq_a6", "FAQ 6: answer", "Submit your company and project details through the enquiry form. The COFUR team can then discuss your requirements and quotation."),
    ("final_eyebrow", "Closing: small label", "Start your project discussion"),
    ("final_title", "Closing: heading", "Planning an Office or Commercial Project?"),
    ("final_text", "Closing: paragraph", "Discuss your acoustic ceiling requirements with COFUR and explore design-led solutions for your workplace."),
    ("final_btn", "Closing: button", "Request project quote"),
    ("footer_link", "Footer: collection link", "View Acoustic Wall Panels Collection"),
]

# Seven designs: title is fixed in the code; the description and photo are editable.
CEILING_DESIGNS = [
    ("Wave", "A flowing acoustic ceiling design for contemporary workplace interiors.", "images/cofur/ceiling-wave.webp"),
    ("Petal", "An organic-inspired ceiling form for visually refined commercial spaces.", "images/cofur/ceiling-petal.webp"),
    ("Blade", "A linear design direction suitable for modern commercial workplace interiors.", "images/cofur/ceiling-blade.webp"),
    ("Planks", "A layered linear ceiling concept for contemporary workplace environments.", "images/cofur/ceiling-planks.webp"),
    ("Grid", "A structured ceiling design for modern commercial interiors.", "images/cofur/ceiling-grid.webp"),
    ("Waffle", "An architectural ceiling pattern for distinctive workplace environments.", "images/cofur/ceiling-waffle.webp"),
    ("Hive", "A geometric ceiling design inspired by honeycomb forms.", "images/cofur/ceiling-hive.webp"),
]

# (key, label, default static file)
CEILING_IMAGES = [
    ("img_hero", "Hero photo", "images/cofur/ceiling-collection.webp"),
] + [
    (f"img_design_{i}", f"{title} photo", photo)
    for i, (title, _copy, photo) in enumerate(CEILING_DESIGNS, start=1)
]

CEILING_TEXT_EXTRA = [
    (f"design_{i}_copy", f"{title}: description", copy)
    for i, (title, copy, _photo) in enumerate(CEILING_DESIGNS, start=1)
]
