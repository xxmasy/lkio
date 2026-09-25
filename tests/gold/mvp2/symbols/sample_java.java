// Gold Fixture: Java Symbols, Overloading, Annotations, and Enum
package com.example.crm;

import org.springframework.web.bind.annotation.*;
import org.springframework.beans.factory.annotation.Autowired;

public enum LeadState {
    DRAFT,
    QUALIFIED,
    CONVERTED
}

@Documented
public @interface AuditLog {
    String action() default "VIEW";
}

@RestController
@RequestMapping("/api/leads")
public class LeadController {

    @Autowired
    private LeadService leadService;

    public LeadController(LeadService leadService) {
        this.leadService = leadService;
    }

    @GetMapping("/{id}")
    public Lead getLeadById(@PathVariable("id") Long id) {
        return leadService.findById(id);
    }

    // Overloaded method: different parameter signature
    @GetMapping("/by-code")
    public Lead getLeadByCode(@RequestParam("code") String code) {
        return leadService.findByCode(code);
    }

    @PostMapping
    public Long createLead(@RequestBody LeadDto dto) {
        return leadService.create(dto);
    }
}
