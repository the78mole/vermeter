import { defineConfig } from "vitepress";
import { withMermaid } from "vitepress-plugin-mermaid";

export default withMermaid(
  defineConfig({
    title: "Rental Manager",
    description:
      "Documentation for Rental Manager – a self-hosted property management platform.",
    base: "/vermeter/",

    head: [["link", { rel: "icon", href: "/vermeter/favicon.ico" }]],

    themeConfig: {
      logo: null,
      siteTitle: "Rental Manager Docs",

      nav: [
        { text: "Home", link: "/" },
        { text: "Architecture", link: "/architecture" },
        { text: "Roles", link: "/roles/" },
        { text: "Domain", link: "/domain/" },
        { text: "Setup", link: "/setup" },
      ],

      sidebar: {
        "/roles/": [
          {
            text: "Roles & Access",
            items: [
              { text: "Overview", link: "/roles/" },
              { text: "Admin / Operator", link: "/roles/admin" },
              { text: "Landlord", link: "/roles/landlord" },
              { text: "Caretaker (Hausverwalter)", link: "/roles/caretaker" },
              { text: "Tenant", link: "/roles/tenant" },
            ],
          },
        ],
        "/domain/": [
          {
            text: "Domain Model",
            items: [
              { text: "Overview", link: "/domain/" },
              { text: "Buildings & Apartments", link: "/domain/buildings" },
              { text: "Contracts & Billing", link: "/domain/contracts" },
            ],
          },
        ],
      },

      socialLinks: [
        { icon: "github", link: "https://github.com/the78mole/vermeter" },
      ],

      footer: {
        message: "Released under the MIT License.",
        copyright: "© 2026 the78mole",
      },

      search: {
        provider: "local",
      },
    },

    // vitepress-plugin-mermaid options
    mermaid: {
      theme: "default",
    },
  }),
);
