import json
import re
import os
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

def main():
    print("="*30)
    print("POKEMON SCRAPER")
    print("Digite o nome do Pokemon para buscar ou 'sair' para encerrar.")
    print("="*30)

    output_dir = "output/pokemon"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    while True:
        try:
            name = input("\nNome do Pokemon: ").strip().lower().replace(" ", "")
        except KeyboardInterrupt:
            print("\nOperacao cancelada pelo usuario.")
            break

        if name in ['sair', 'exit']:
            print("Encerrando programa.")
            break

        if not name:
            continue

        print(f"Iniciando busca por: {name}")
        print("Abrindo navegador...")

        driver = None
        try:
            driver = uc.Chrome(version_main=144)
            wait = WebDriverWait(driver, 10)

            url = f"https://www.pokemon.com/br/pokedex/{name}"
            print(f"Acessando: {url}")
            driver.get(url)

            try:
                error_element = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.page-main-title"))
                )
                if "página não encontrada" in error_element.text.lower():
                    print(f"Erro: Pokemon '{name}' nao encontrado.")
                    continue
            except TimeoutException:
                pass 

            print("Carregando dados...")
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".pokedex-pokemon-pagination-title")))
                wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".pokemon-ability-info.active")))
            except TimeoutException:
                print(f"Erro: Tempo limite excedido. Nao foi possivel carregar os dados de '{name}'.")
                continue

            header = driver.find_element(By.CLASS_NAME, "pokedex-pokemon-pagination-title")
            raw_text = header.text.replace('\n', ' ').strip()

            match = re.search(r'(.+?)\s*Nº\s*(\d+)', raw_text)
            if match:
                p_name = match.group(1).strip()
                p_number_str = match.group(2).strip()
            else:
                p_name = raw_text
                p_number_str = ""

            display_name = f"{p_name} Nº {p_number_str}"
            
            try:
                img_url = driver.find_element(By.CSS_SELECTOR, ".profile-images img.active").get_attribute("src")
            except:
                img_url = ""

            stats_map = {
                "PS": "hp", "Ataque": "attack", "Defesa": "defense",
                "Ataque Especial": "sp_attack", "Defesa Especial": "sp_defense",
                "Velocidade": "speed"
            }
            stats = {}
            stat_rows = driver.find_elements(By.CSS_SELECTOR, ".pokemon-stats-info.active > ul > li")
            for row in stat_rows:
                try:
                    label = row.find_element(By.TAG_NAME, "span").text.strip()
                    if label in stats_map:
                        val = row.find_element(By.CSS_SELECTOR, ".meter").get_attribute("data-value")
                        stats[stats_map[label]] = int(val)
                except: pass

            container_abilities = driver.find_element(By.CSS_SELECTOR, ".pokemon-ability-info.active")
            
            def get_attribute_text(xpath):
                try:
                    return container_abilities.find_element(By.XPATH, xpath).text.strip()
                except: return ""

            height = get_attribute_text(".//span[contains(text(), 'Altura')]/following-sibling::span")
            weight = get_attribute_text(".//span[contains(text(), 'Peso')]/following-sibling::span")
            category_val = get_attribute_text(".//span[contains(text(), 'Categoria')]/following-sibling::span")
            
            category = {"value": category_val}

            abilities_data = []
            try:
                container_abilities = driver.find_element(By.CSS_SELECTOR, ".pokemon-ability-info.active")
                ability_buttons = container_abilities.find_elements(By.CSS_SELECTOR, ".attribute-list .moreInfo")
                count = len(ability_buttons)
            except: count = 0

            if count == 0:
                try:
                    static_abs = driver.find_elements(By.CSS_SELECTOR, ".pokemon-ability-info.active .attribute-list .attribute-value")
                    for ab in static_abs:
                        abilities_data.append(ab.text.strip())
                except: pass
            else:
                for i in range(count):
                    try:
                        container_abilities = driver.find_element(By.CSS_SELECTOR, ".pokemon-ability-info.active")
                        btn = container_abilities.find_elements(By.CSS_SELECTOR, ".attribute-list .moreInfo")[i]
                        
                        driver.execute_script("arguments[0].click();", btn)
                        
                        modal = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".pokemon-ability-info-detail")))
                        ab_name = modal.find_element(By.TAG_NAME, "h3").text.strip()
                        ab_desc = modal.find_element(By.TAG_NAME, "p").text.strip()
                        
                        abilities_data.append({"name": ab_name, "description": ab_desc})
                        
                        close_btn = modal.find_element(By.CLASS_NAME, "button-close")
                        driver.execute_script("arguments[0].click();", close_btn)
                        
                        time.sleep(0.5)
                        try:
                            WebDriverWait(driver, 2).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".pokemon-ability-info-detail")))
                        except: pass
                    except Exception as e:
                        try:
                            container_abilities = driver.find_element(By.CSS_SELECTOR, ".pokemon-ability-info.active")
                            btn_fb = container_abilities.find_elements(By.CSS_SELECTOR, ".attribute-list .moreInfo")[i]
                            abilities_data.append(btn_fb.find_element(By.CLASS_NAME, "attribute-value").text.strip())
                        except: pass

            types = [t.text.strip() for t in driver.find_elements(By.CSS_SELECTOR, ".dtm-type ul li a") if t.text.strip()]
            weaknesses = [w.text.strip() for w in driver.find_elements(By.CSS_SELECTOR, ".dtm-weaknesses ul li a span") if w.text.strip()]

            evolution_data = {}
            try:
                evo_section = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "evolution-profile")))

                def parse_evo_card(card):
                    try:
                        text = card.text.replace('\n', ' ').strip()
                        match = re.search(r'(.+?)\s*Nº\s*(\d+)', text)
                        if match:
                            c_name = match.group(1).strip()
                            c_num = match.group(2).strip()
                        else:
                            try:
                                c_name = card.find_element(By.TAG_NAME, "h3").text.split("Nº")[0].strip()
                            except: c_name = text
                            try:
                                c_num = card.find_element(By.CLASS_NAME, "pokemon-number").text.replace("Nº", "").strip()
                            except: c_num = ""
                        
                        if not c_name: return None

                        c_types = [t.text.strip() for t in card.find_elements(By.CSS_SELECTOR, ".evolution-attributes li") if t.text.strip()]
                        try:
                            c_img = card.find_element(By.TAG_NAME, "img").get_attribute("src")
                        except: c_img = ""

                        return {
                            "name": c_name,
                            "number": c_num,
                            "type": c_types,
                            "image_url": c_img
                        }
                    except: return None

                raw_chain = []
                stages = evo_section.find_elements(By.XPATH, "./li")

                for stage in stages:
                    sub_uls = stage.find_elements(By.TAG_NAME, "ul")
                    pokemon_ul = None
                    for ul in sub_uls:
                        if "evolution-attributes" not in ul.get_attribute("class"):
                            pokemon_ul = ul
                            break
                    
                    if pokemon_ul:
                        branch_data = []
                        links = pokemon_ul.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            data = parse_evo_card(link)
                            if data: branch_data.append(data)
                        if branch_data:
                            raw_chain.append({"type": "multi", "data": branch_data})
                    else:
                        try:
                            link = stage.find_element(By.TAG_NAME, "a")
                            data = parse_evo_card(link)
                            if data:
                                raw_chain.append({"type": "single", "data": data})
                        except: pass

                evolution_chain = {}
                if raw_chain:
                    if raw_chain[0]["type"] == "single":
                        evolution_chain["base"] = raw_chain[0]["data"]
                    
                    chain_stages = []
                    for i in range(1, len(raw_chain)):
                        step = raw_chain[i]
                        if step["type"] == "single":
                            chain_stages.append({"stage": i, "pokemon": step["data"]})
                        else:
                            chain_stages.append({"stage": i, "branches": step["data"]})
                    
                    if chain_stages:
                        evolution_chain["stages"] = chain_stages
                
                evolution_data["evolution_chain"] = evolution_chain

                current_pos = -1
                is_inside_multi = False
                
                for idx, step in enumerate(raw_chain):
                    if step["type"] == "single":
                        if step["data"]["name"].lower() == p_name.lower():
                            current_pos = idx
                            break
                    elif step["type"] == "multi":
                        for sub_p in step["data"]:
                            if sub_p["name"].lower() == p_name.lower():
                                current_pos = idx
                                is_inside_multi = True
                                break
                    if current_pos != -1: break
                
                if current_pos > 0:
                    prev_step = raw_chain[current_pos - 1]
                    if prev_step["type"] == "single":
                        evolution_data["evolves_from"] = prev_step["data"]
                
                if not is_inside_multi and (current_pos + 1 < len(raw_chain)):
                    next_step = raw_chain[current_pos + 1]
                    if next_step["type"] == "single":
                        evolution_data["evolves_to"] = next_step["data"]
                    elif next_step["type"] == "multi":
                        evolution_data["evolves_to"] = next_step["data"]

            except Exception as e:
                pass

            pokemon_data = {
                "name": p_name,
                "display_name": display_name,
                "number": p_number_str,
                "image_url": img_url,
                "type": types,
                "stats": stats,
                "weaknesses": weaknesses,
                "height": height,
                "weight": weight,
                "category": category,
                "abilities": abilities_data
            }
            pokemon_data.update(evolution_data)

            filename = os.path.join(output_dir, f"{p_name.lower()}_{p_number_str}.json")
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(pokemon_data, f, indent=2, ensure_ascii=False)

            print(f"Sucesso: Dados salvos em '{filename}'")

        except Exception as e:
            print(f"Erro inesperado: {e}")
        finally:
            if driver:
                print("Fechando navegador...")
                try:
                    driver.quit()
                except: pass
            print("-" * 30)

if __name__ == "__main__":
    main()
